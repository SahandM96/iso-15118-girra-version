"""
This module contains the EVCC's States used to process the SECC's incoming
V2GMessage objects of the ISO 15118-2 protocol, from SessionSetupRes to
SessionStopRes.
"""

import logging
from time import time
from typing import List, Union

from iso15118.evcc import evcc_settings
from iso15118.evcc.comm_session_handler import EVCCCommunicationSession
from iso15118.evcc.states.evcc_state import StateEVCC
from iso15118.shared.exceptions import DecryptionError, PrivateKeyReadError
from iso15118.shared.exi_codec import EXI
from iso15118.shared.messages.app_protocol import (
    SupportedAppProtocolReq,
    SupportedAppProtocolRes,
)
from iso15118.shared.messages.enums import AuthEnum, Namespace, Protocol
from iso15118.shared.messages.iso15118_2.body import (
    EMAID,
    AuthorizationReq,
    AuthorizationRes,
    CertificateInstallationReq,
    CertificateInstallationRes,
    ChargeParameterDiscoveryReq,
    ChargeParameterDiscoveryRes,
    ChargingStatusReq,
    ChargingStatusRes,
    CurrentDemandReq,
    MeteringReceiptReq,
    MeteringReceiptRes,
    PaymentDetailsReq,
    PaymentDetailsRes,
    PaymentServiceSelectionReq,
    PaymentServiceSelectionRes,
    PowerDeliveryReq,
    PowerDeliveryRes,
    ServiceDetailReq,
    ServiceDetailRes,
    ServiceDiscoveryReq,
    ServiceDiscoveryRes,
    SessionSetupRes,
    SessionStopReq,
    SessionStopRes,
)
from iso15118.shared.messages.iso15118_2.datatypes import (
    ACEVSEStatus,
    ChargeProgress,
    ChargeService,
    ChargingSession,
    EnergyTransferModeEnum,
    EVSENotification,
    EVSEProcessing,
    RootCertificateIDList,
    SelectedService,
    SelectedServiceList,
    ServiceCategory,
    ServiceID,
)
from iso15118.shared.messages.iso15118_2.msgdef import V2GMessage as V2GMessageV2
from iso15118.shared.messages.iso15118_2.timeouts import Timeouts
from iso15118.shared.messages.iso15118_20.common_types import (
    V2GMessage as V2GMessageV20,
)
from iso15118.shared.messages.timeouts import Timeouts as TimeoutsShared
from iso15118.shared.messages.xmldsig import X509IssuerSerial
from iso15118.shared.notifications import StopNotification
from iso15118.shared.security import (
    CertPath,
    KeyEncoding,
    KeyPath,
    create_signature,
    decrypt_priv_key,
    get_cert_cn,
    get_cert_issuer_serial,
    load_cert,
    load_cert_chain,
    load_priv_key,
    to_ec_pub_key,
    verify_signature,
)
from iso15118.shared.states import Terminate

logger = logging.getLogger(__name__)


# ============================================================================
# |    COMMON EVCC STATES (FOR BOTH AC AND DC CHARGING) - ISO 15118-2        |
# ============================================================================


class SessionSetup(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a SessionSetupRes from
    the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        # TODO: less the time used for waiting for and processing the
        #       SDPResponse and SupportedAppProtocolRes
        super().__init__(
            comm_session, TimeoutsShared.V2G_EVCC_COMMUNICATION_SETUP_TIMEOUT
        )

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, SessionSetupRes)
        if not msg:
            return

        session_setup_res: SessionSetupRes = msg.body.session_setup_res

        self.comm_session.session_id = msg.header.session_id
        self.comm_session.evse_id = session_setup_res.evse_id

        self.create_next_message(
            ServiceDiscovery,
            ServiceDiscoveryReq(),
            Timeouts.SERVICE_DISCOVERY_REQ,
            Namespace.ISO_V2_MSG_DEF,
        )


class ServiceDiscovery(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a ServiceDiscoveryRes from
    the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.SERVICE_DISCOVERY_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, ServiceDiscoveryRes)
        if not msg:
            return

        service_discovery_res: ServiceDiscoveryRes = msg.body.service_discovery_res

        if not service_discovery_res.charge_service:
            self.stop_state_machine("ChargeService not offered")
            return

        self.select_auth_mode(service_discovery_res.auth_option_list.auth_options)
        self.select_services(service_discovery_res)
        self.select_energy_transfer_mode()

        charge_service: ChargeService = service_discovery_res.charge_service
        offered_energy_modes: List[
            EnergyTransferModeEnum
        ] = charge_service.supported_energy_transfer_mode.energy_modes

        if self.comm_session.selected_energy_mode not in offered_energy_modes:
            self.stop_state_machine(
                f"Offered energy transfer modes "
                f"{offered_energy_modes} not compatible with "
                f"{self.comm_session.selected_energy_mode}"
            )
            return

        if len(self.comm_session.service_details_to_request) == 0:
            payment_service_selection_req = PaymentServiceSelectionReq(
                selected_auth_option=self.comm_session.selected_auth_option,
                selected_service_list=SelectedServiceList(
                    selected_service=self.comm_session.selected_services
                ),
            )

            self.create_next_message(
                PaymentServiceSelection,
                payment_service_selection_req,
                Timeouts.PAYMENT_SERVICE_SELECTION_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        else:
            service_detail_req = ServiceDetailReq(
                service_id=self.comm_session.service_details_to_request.pop()
            )

            self.create_next_message(
                ServiceDetail,
                service_detail_req,
                Timeouts.SERVICE_DETAIL_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )

    def select_energy_transfer_mode(self):
        """
        Check if an energy transfer mode was saved from a previously paused
        communication session and reuse for resumed session, otherwise request
        from EV controller.
        """
        if evcc_settings.RESUME_REQUESTED_ENERGY_MODE:
            logger.debug(
                "Reusing energy transfer mode "
                f"{evcc_settings.RESUME_REQUESTED_ENERGY_MODE} "
                "from previously paused session"
            )
            self.comm_session.selected_energy_mode = (
                evcc_settings.RESUME_REQUESTED_ENERGY_MODE
            )
            evcc_settings.RESUME_REQUESTED_ENERGY_MODE = None
        else:
            self.comm_session.selected_energy_mode = (
                self.comm_session.ev_controller.get_energy_transfer_mode()
            )

    def select_auth_mode(self, auth_option_list: List[AuthEnum]):
        """
        Check if an authorization mode (aka payment option in ISO 15118-2) was
        saved from a previously paused communication session and reuse for
        resumed session, otherwise request from EV controller.
        """
        if evcc_settings.RESUME_SELECTED_AUTH_OPTION:
            logger.debug(
                "Reusing authorization option "
                f"{evcc_settings.RESUME_SELECTED_AUTH_OPTION} "
                "from previously paused session"
            )
            self.comm_session.selected_auth_option = (
                evcc_settings.RESUME_SELECTED_AUTH_OPTION
            )
            evcc_settings.RESUME_SELECTED_AUTH_OPTION = None
        else:
            # Choose Plug & Charge (pnc) or External Identification Means (eim)
            # as the selected authorization option. The car manufacturer might
            # have a mechanism to determine a user-defined or default
            # authorization option. This implementation favors pnc, but
            # feel free to change if need be.
            if AuthEnum.PNC_V2 in auth_option_list and self.comm_session.is_tls:
                self.comm_session.selected_auth_option = AuthEnum.PNC_V2
            else:
                self.comm_session.selected_auth_option = AuthEnum.EIM_V2

    def select_services(self, service_discovery_res: ServiceDiscoveryRes):
        """
        According to [V2G2-422], a ServiceDetailReq is needed in case VAS
        (value added services) such as certificate installation/update are to
        be used and offered by the SECC. Furthermore, it must be checked if VAS
        are allowed (-> only if TLS connection is used).

        The mandatory ChargeService is not a VAS, though.
        """
        # Add the ChargeService as a selected service
        self.comm_session.selected_services.append(
            SelectedService(service_id=service_discovery_res.charge_service.service_id)
        )

        if not self.comm_session.is_tls or service_discovery_res.service_list is None:
            return

        offered_services: str = ""

        for service in service_discovery_res.service_list.services:
            offered_services += (
                "\nService ID: "
                f"{service.service_id}, "
                "Service name: "
                f"{service.service_name}"
            )
            if (
                service.service_category == ServiceCategory.CERTIFICATE
                and self.comm_session.selected_auth_option
                and self.comm_session.selected_auth_option == AuthEnum.PNC_V2
                and self.comm_session.ev_controller.is_cert_install_needed()
            ):
                # Make sure to send a ServiceDetailReq for the
                # Certificate service
                self.comm_session.service_details_to_request.append(service.service_id)

                # TODO We should actually first ask for the ServiceDetails and
                #      based on the service parameter list make absolutely sure
                #      that the certificate installation service is offered,
                #      as it would make sense (but just to be fail-proof)
                self.comm_session.selected_services.append(
                    SelectedService(service_id=ServiceID.CERTIFICATE)
                )

            # Request more service details if you're interested in e.g.
            # an Internet service or a use case-specific service

        logger.debug(f"Offered value-added services: {offered_services}")


class ServiceDetail(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a ServiceDetailReq
    from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.SERVICE_DETAIL_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, ServiceDetailRes)
        if not msg:
            return

        # service_detail_res: ServiceDetailRes = msg.body.service_detail_res

        # If you want to further evaluate the service details, then do so here
        # TODO Make sure to check the parameter list and add the certificate
        #      service to the list of selected services here (instead of
        #      directly in the ServiceDiscovery

        if len(self.comm_session.service_details_to_request) == 0:
            payment_service_selection_req = PaymentServiceSelectionReq(
                selected_auth_option=self.comm_session.selected_auth_option,
                selected_service_list=SelectedServiceList(
                    selected_service=self.comm_session.selected_services
                ),
            )

            self.create_next_message(
                PaymentServiceSelection,
                payment_service_selection_req,
                Timeouts.PAYMENT_SERVICE_SELECTION_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        else:
            service_detail_req = ServiceDetailReq(
                service_id=self.comm_session.service_details_to_request.pop()
            )

            self.create_next_message(
                ServiceDetail,
                service_detail_req,
                Timeouts.SERVICE_DETAIL_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )


class PaymentServiceSelection(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    PaymentServiceSelectionRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.PAYMENT_SERVICE_SELECTION_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, PaymentServiceSelectionRes)
        if not msg:
            return

        if (
            self.comm_session.selected_auth_option
            and self.comm_session.selected_auth_option == AuthEnum.PNC_V2
        ):
            if self.comm_session.ev_controller.is_cert_install_needed():
                # TODO: Find a more generic way to serach for all available
                #       V2GRootCA certificates
                issuer, serial = get_cert_issuer_serial(CertPath.V2G_ROOT_DER)
                cert_install_req = CertificateInstallationReq(
                    id="id1",
                    oem_provisioning_cert=load_cert(CertPath.OEM_LEAF_DER),
                    list_of_root_cert_ids=RootCertificateIDList(
                        x509_issuer_serials=[
                            X509IssuerSerial(
                                x509_issuer_name=issuer, x509_serial_number=serial
                            )
                        ]
                    ),
                )

                try:
                    signature = create_signature(
                        [
                            (
                                cert_install_req.id,
                                EXI().to_exi(
                                    cert_install_req, Namespace.ISO_V2_MSG_DEF
                                ),
                            )
                        ],
                        load_priv_key(KeyPath.OEM_LEAF_PEM, KeyEncoding.PEM),
                    )

                    self.create_next_message(
                        CertificateInstallation,
                        cert_install_req,
                        Timeouts.CERTIFICATE_INSTALLATION_REQ,
                        Namespace.ISO_V2_MSG_DEF,
                        signature=signature,
                    )
                except PrivateKeyReadError as exc:
                    self.stop_state_machine(
                        "Can't read private key necessary to sign "
                        f"CertificateInstallationReq: {exc}"
                    )
                    return
            else:
                try:
                    payment_details_req = PaymentDetailsReq(
                        emaid=EMAID(
                            value=get_cert_cn(load_cert(CertPath.CONTRACT_LEAF_DER))
                        ),
                        cert_chain=load_cert_chain(
                            protocol=Protocol.ISO_15118_2,
                            leaf_path=CertPath.CONTRACT_LEAF_DER,
                            sub_ca2_path=CertPath.MO_SUB_CA2_DER,
                            sub_ca1_path=CertPath.MO_SUB_CA1_DER,
                        ),
                    )
                except FileNotFoundError as exc:
                    self.stop_state_machine(f"Can't find file {exc.filename}")
                    return

                self.create_next_message(
                    PaymentDetails,
                    payment_details_req,
                    Timeouts.PAYMENT_DETAILS_REQ,
                    Namespace.ISO_V2_MSG_DEF,
                )
        else:
            self.create_next_message(
                Authorization,
                AuthorizationReq(),
                Timeouts.AUTHORIZATION_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )


class CertificateInstallation(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    PaymentServiceSelectionRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.CERTIFICATE_INSTALLATION_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, CertificateInstallationRes)
        if not msg:
            return

        cert_install_res: CertificateInstallationRes = (
            msg.body.certificate_installation_res
        )

        if not verify_signature(
            signature=msg.header.signature,
            elements_to_sign=[
                (
                    cert_install_res.contract_cert_chain.id,
                    EXI().to_exi(
                        cert_install_res.contract_cert_chain, Namespace.ISO_V2_MSG_DEF
                    ),
                ),
                (
                    cert_install_res.encrypted_private_key.id,
                    EXI().to_exi(
                        cert_install_res.encrypted_private_key, Namespace.ISO_V2_MSG_DEF
                    ),
                ),
                (
                    cert_install_res.dh_public_key.id,
                    EXI().to_exi(
                        cert_install_res.dh_public_key, Namespace.ISO_V2_MSG_DEF
                    ),
                ),
                (
                    cert_install_res.emaid.id,
                    EXI().to_exi(cert_install_res.emaid, Namespace.ISO_V2_MSG_DEF),
                ),
            ],
            leaf_cert=cert_install_res.cps_cert_chain.certificate,
            sub_ca_certs=cert_install_res.cps_cert_chain.sub_certificates.certificates,
            root_ca_cert_path=CertPath.V2G_ROOT_DER,
        ):
            self.stop_state_machine(
                "Signature verification of " "CertificateInstallationRes failed"
            )
            return

        try:
            decrypted_priv_key = decrypt_priv_key(
                encrypted_priv_key_with_iv=cert_install_res.encrypted_private_key.value,
                ecdh_priv_key=load_priv_key(KeyPath.OEM_LEAF_PEM, KeyEncoding.PEM),
                ecdh_pub_key=to_ec_pub_key(cert_install_res.dh_public_key.value),
            )

            self.comm_session.ev_controller.store_contract_cert_and_priv_key(
                cert_install_res.contract_cert_chain.certificate, decrypted_priv_key
            )
        except DecryptionError:
            self.stop_state_machine(
                "Can't decrypt encrypted private key for contract " "certificate"
            )
            return
        except PrivateKeyReadError as exc:
            self.stop_state_machine(
                "Can't read private key needed to decrypt "
                "encrypted private key contained in "
                f"CertificateInstallationRes. {exc}"
            )
            return

        payment_details_req = PaymentDetailsReq(
            emaid=get_cert_cn(load_cert(CertPath.CONTRACT_LEAF_DER)),
            cert_chain=load_cert_chain(
                protocol=Protocol.ISO_15118_2,
                leaf_path=CertPath.CONTRACT_LEAF_DER,
                sub_ca2_path=CertPath.MO_SUB_CA2_DER,
                sub_ca1_path=CertPath.MO_SUB_CA1_DER,
            ),
        )

        self.create_next_message(
            PaymentDetails,
            payment_details_req,
            Timeouts.PAYMENT_DETAILS_REQ,
            Namespace.ISO_V2_MSG_DEF,
        )


class PaymentDetails(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    AuthorizationRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.PAYMENT_DETAILS_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, PaymentDetailsRes)
        if not msg:
            return

        payment_details_res: PaymentDetailsRes = msg.body.payment_details_res

        authorization_req = AuthorizationReq(
            id="id1", gen_challenge=payment_details_res.gen_challenge
        )

        try:
            signature = create_signature(
                [
                    (
                        authorization_req.id,
                        EXI().to_exi(authorization_req, Namespace.ISO_V2_MSG_DEF),
                    )
                ],
                load_priv_key(KeyPath.CONTRACT_LEAF_PEM, KeyEncoding.PEM),
            )

            self.create_next_message(
                Authorization,
                authorization_req,
                Timeouts.AUTHORIZATION_REQ,
                Namespace.ISO_V2_MSG_DEF,
                signature=signature,
            )
        except PrivateKeyReadError as exc:
            self.stop_state_machine(
                f"Can't read private key to sign AuthorizationReq: " f"{exc}"
            )
            return


class Authorization(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    AuthorizationRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.AUTHORIZATION_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, AuthorizationRes)
        if not msg:
            return

        authorization_res: AuthorizationRes = msg.body.authorization_res

        if authorization_res.evse_processing == EVSEProcessing.FINISHED:
            # Reset the Ongoing timer
            self.comm_session.ongoing_timer = -1

            charge_params = self.comm_session.ev_controller.get_charge_params_v2()

            charge_parameter_discovery_req = ChargeParameterDiscoveryReq(
                requested_energy_mode=charge_params.energy_mode,
                ac_ev_charge_parameter=charge_params.ac_parameters,
                dc_ev_charge_parameter=charge_params.dc_parameters,
            )

            self.create_next_message(
                ChargeParameterDiscovery,
                charge_parameter_discovery_req,
                Timeouts.CHARGE_PARAMETER_DISCOVERY_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        else:
            logger.debug("SECC is still processing the Authorization")
            elapsed_time: float = 0
            if self.comm_session.ongoing_timer >= 0:
                elapsed_time = time() - self.comm_session.ongoing_timer
                if elapsed_time > TimeoutsShared.V2G_EVCC_ONGOING_TIMEOUT:
                    self.stop_state_machine(
                        "Ongoing timer timed out for " "AuthorizationRes"
                    )
                    return
            else:
                self.comm_session.ongoing_timer = time()

            self.create_next_message(
                Authorization,
                AuthorizationReq(),
                min(
                    Timeouts.AUTHORIZATION_REQ,
                    TimeoutsShared.V2G_EVCC_ONGOING_TIMEOUT - elapsed_time,
                ),
                Namespace.ISO_V2_MSG_DEF,
            )


class ChargeParameterDiscovery(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    ChargeParameterDiscoveryRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.CHARGE_PARAMETER_DISCOVERY_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, ChargeParameterDiscoveryRes)
        if not msg:
            return

        charge_params_res: ChargeParameterDiscoveryRes = (
            msg.body.charge_parameter_discovery_res
        )

        if charge_params_res.evse_processing == EVSEProcessing.FINISHED:
            # Reset the Ongoing timer
            self.comm_session.ongoing_timer = -1

            # TODO Look at EVSEStatus and EVSENotification and react accordingly
            #      if e.g. EVSENotification is set to STOP_CHARGING or if RCD
            #      is True. But let's do that after the testival

            (
                charge_progress,
                schedule_id,
                charging_profile,
            ) = self.comm_session.ev_controller.process_sa_schedules(
                charge_params_res.sa_schedule_list.values
            )

            power_delivery_req = PowerDeliveryReq(
                charge_progress=charge_progress,
                sa_schedule_tuple_id=schedule_id,
                charging_profile=charging_profile,
            )

            self.create_next_message(
                PowerDelivery,
                power_delivery_req,
                Timeouts.POWER_DELIVERY_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )

            self.comm_session.selected_schedule = schedule_id

            # TODO Set CP state to C max. 250 ms after sending PowerDeliveryReq
        else:
            logger.debug(
                "SECC is still processing the proposed charging "
                "schedule and charge parameters"
            )
            elapsed_time: float = 0
            if self.comm_session.ongoing_timer >= 0:
                elapsed_time = time() - self.comm_session.ongoing_timer
                if elapsed_time > TimeoutsShared.V2G_EVCC_ONGOING_TIMEOUT:
                    self.stop_state_machine(
                        "Ongoing timer timed out for " "ChargeParameterDiscoveryRes"
                    )
                    return
            else:
                self.comm_session.ongoing_timer = time()

            charge_params = self.comm_session.ev_controller.get_charge_params_v2()

            charge_parameter_discovery_req = ChargeParameterDiscoveryReq(
                requested_energy_mode=charge_params.energy_mode,
                ac_ev_charge_parameter=charge_params.ac_parameters,
                dc_ev_charge_parameter=charge_params.dc_parameters,
            )

            self.create_next_message(
                ChargeParameterDiscovery,
                charge_parameter_discovery_req,
                min(
                    Timeouts.CHARGE_PARAMETER_DISCOVERY_REQ,
                    TimeoutsShared.V2G_EVCC_ONGOING_TIMEOUT - elapsed_time,
                ),
                Namespace.ISO_V2_MSG_DEF,
            )


class PowerDelivery(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    PowerDeliveryRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.POWER_DELIVERY_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, PowerDeliveryRes)
        if not msg:
            return

        if self.comm_session.charging_session_stop:
            session_stop_req = SessionStopReq(
                charging_session=self.comm_session.charging_session_stop
            )
            self.create_next_message(
                SessionStop,
                session_stop_req,
                Timeouts.SESSION_STOP_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        elif self.comm_session.renegotiation_requested:
            self.comm_session.renegotiation_requested = False

            charge_params = self.comm_session.ev_controller.get_charge_params_v2()

            charge_parameter_discovery_req = ChargeParameterDiscoveryReq(
                requested_energy_mode=charge_params.energy_mode,
                ac_ev_charge_parameter=charge_params.ac_parameters,
                dc_ev_charge_parameter=charge_params.dc_parameters,
            )

            self.create_next_message(
                ChargeParameterDiscovery,
                charge_parameter_discovery_req,
                Timeouts.CHARGE_PARAMETER_DISCOVERY_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        elif (
            self.comm_session.selected_energy_mode
            and self.comm_session.selected_energy_mode.value.startswith("AC")
        ):
            self.create_next_message(
                ChargingStatus,
                ChargingStatusReq(),
                Timeouts.CHARGING_STATUS_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        else:
            self.create_next_message(
                CurrentDemand,
                # TODO: Create proper CurrentDemandReq
                CurrentDemandReq(),
                Timeouts.CHARGING_STATUS_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )


class ChargingStatus(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    ChargingStatusRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.CHARGING_STATUS_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, ChargingStatusRes)
        if not msg:
            return

        charging_status_res: ChargingStatusRes = msg.body.charging_status_res
        ac_evse_status: ACEVSEStatus = charging_status_res.ac_evse_status

        if charging_status_res.receipt_required and self.comm_session.is_tls:
            logger.debug("SECC requested MeteringReceipt")

            metering_receipt_req = MeteringReceiptReq(
                id="id1",
                session_id=self.comm_session.session_id,
                sa_schedule_tuple_id=charging_status_res.sa_schedule_tuple_id,
                meter_info=charging_status_res.meter_info,
            )

            try:
                signature = create_signature(
                    [
                        (
                            metering_receipt_req.id,
                            EXI().to_exi(
                                metering_receipt_req, Namespace.ISO_V2_MSG_DEF
                            ),
                        )
                    ],
                    load_priv_key(KeyPath.CONTRACT_LEAF_PEM, KeyEncoding.PEM),
                )

                self.create_next_message(
                    MeteringReceipt,
                    metering_receipt_req,
                    Timeouts.METERING_RECEIPT_REQ,
                    Namespace.ISO_V2_MSG_DEF,
                    signature=signature,
                )
            except PrivateKeyReadError as exc:
                self.stop_state_machine(
                    "Can't read private key necessary to sign "
                    f"MeteringReceiptReq: {exc}"
                )
                return
        elif ac_evse_status.evse_notification == EVSENotification.RE_NEGOTIATION:
            self.comm_session.renegotiation_requested = True
            power_delivery_req = PowerDeliveryReq(
                charge_progress=ChargeProgress.RENEGOTIATE,
                sa_schedule_tuple_id=self.comm_session.selected_schedule,
            )
            self.create_next_message(
                PowerDelivery,
                power_delivery_req,
                Timeouts.POWER_DELIVERY_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
            logger.debug(f"ChargeProgress is set to {ChargeProgress.RENEGOTIATE}")
        elif ac_evse_status.evse_notification == EVSENotification.STOP_CHARGING:
            self.stop_charging()

        elif self.comm_session.ev_controller.continue_charging():
            self.create_next_message(
                ChargingStatus,
                ChargingStatusReq(),
                Timeouts.CHARGING_STATUS_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        else:
            self.stop_charging()

    def stop_charging(self):
        power_delivery_req = PowerDeliveryReq(
            charge_progress=ChargeProgress.STOP,
            sa_schedule_tuple_id=self.comm_session.selected_schedule,
        )
        self.create_next_message(
            PowerDelivery,
            power_delivery_req,
            Timeouts.POWER_DELIVERY_REQ,
            Namespace.ISO_V2_MSG_DEF,
        )
        self.comm_session.charging_session_stop = ChargingSession.TERMINATE
        # TODO Implement also a mechanism for pausing
        logger.debug(f"ChargeProgress is set to {ChargeProgress.STOP}")


class CurrentDemand(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    CurrentDemandRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.CHARGING_STATUS_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):

        raise NotImplementedError("CurrentDemand not yet implemented")


class MeteringReceipt(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    MeteringReceiptRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.METERING_RECEIPT_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, MeteringReceiptRes)
        if not msg:
            return

        metering_receipt_res: MeteringReceiptRes = msg.body.metering_receipt_res

        if metering_receipt_res.ac_evse_status:
            notification = metering_receipt_res.ac_evse_status.evse_notification
        else:
            notification = metering_receipt_res.dc_evse_status.evse_notification

        if notification == EVSENotification.STOP_CHARGING:
            logger.debug("SECC requested to stop the charging session")
            self.create_next_message(
                PowerDelivery,
                PowerDeliveryReq(
                    charge_progress=ChargeProgress.STOP,
                    sa_schedule_tuple_id=self.comm_session.selected_schedule,
                ),
                Timeouts.POWER_DELIVERY_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        elif notification == EVSENotification.RE_NEGOTIATION:
            logger.debug("SECC requested a renegotiation")
            self.comm_session.renegotiation_requested = True
            self.create_next_message(
                PowerDelivery,
                PowerDeliveryReq(
                    charge_progress=ChargeProgress.RENEGOTIATE,
                    sa_schedule_tuple_id=self.comm_session.selected_schedule,
                ),
                Timeouts.POWER_DELIVERY_REQ,
                Namespace.ISO_V2_MSG_DEF,
            )
        else:
            if (
                self.comm_session.selected_energy_mode
                and self.comm_session.selected_energy_mode.value.startswith("AC")
            ):
                self.create_next_message(
                    ChargingStatus,
                    ChargingStatusReq(),
                    Timeouts.CHARGING_STATUS_REQ,
                    Namespace.ISO_V2_MSG_DEF,
                )
            else:
                self.create_next_message(
                    CurrentDemand,
                    # TODO Create proper CurrentDemandReq
                    CurrentDemandReq(),
                    Timeouts.CHARGING_STATUS_REQ,
                    Namespace.ISO_V2_MSG_DEF,
                )


class SessionStop(StateEVCC):
    """
    The ISO 15118-2 state in which the EVCC processes a
    SessionStopRes from the SECC.
    """

    def __init__(self, comm_session: EVCCCommunicationSession):
        super().__init__(comm_session, Timeouts.SESSION_STOP_REQ)

    def process_message(
        self,
        message: Union[
            SupportedAppProtocolReq,
            SupportedAppProtocolRes,
            V2GMessageV2,
            V2GMessageV20,
        ],
    ):
        msg = self.check_msg_v2(message, SessionStopRes)
        if not msg:
            return

        if self.comm_session.charging_session_stop == ChargingSession.TERMINATE:
            stopped = "terminated"
        else:
            stopped = "paused"

        self.comm_session.stop_reason = StopNotification(
            True,
            f"Communication session {stopped} successfully",
            self.comm_session.writer.get_extra_info("peername"),
        )

        self.next_state = Terminate

        return