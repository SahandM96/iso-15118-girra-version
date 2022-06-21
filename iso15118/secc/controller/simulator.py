"""
This module contains the code to retrieve (hardware-related) data from the EVSE
(Electric Vehicle Supply Equipment).
"""
import logging
import os
import pickle

import zmq
import json
import time
from dataclasses import dataclass
from typing import List, Optional, Union

from aiofile import async_open
from pydantic import BaseModel, Field

from iso15118.secc.controller.interface import EVSEControllerInterface
from iso15118.secc.states.secc_state import StateSECC
from iso15118.shared.messages.datatypes import (
    DCEVSEChargeParameter,
    DCEVSEStatus,
    DCEVSEStatusCode, EVSENotification,
)
from iso15118.shared.messages.datatypes import EVSENotification as EVSENotificationV2
from iso15118.shared.messages.datatypes import (
    PVEVSEMaxCurrentLimit,
    PVEVSEMaxPowerLimit,
    PVEVSEMaxVoltageLimit,
    PVEVSEMinCurrentLimit,
    PVEVSEMinVoltageLimit,
    PVEVSEPeakCurrentRipple,
    PVEVSEPresentCurrent,
    PVEVSEPresentVoltage,
    PVEVTargetCurrent,
    PVEVTargetVoltage,
)
from iso15118.shared.messages.din_spec.datatypes import (
    PMaxScheduleEntry as PMaxScheduleEntryDINSPEC,
)
from iso15118.shared.messages.din_spec.datatypes import (
    PMaxScheduleEntryDetails as PMaxScheduleEntryDetailsDINSPEC,
)
from iso15118.shared.messages.din_spec.datatypes import (
    RelativeTimeInterval as RelativeTimeIntervalDINSPEC,
)
from iso15118.shared.messages.din_spec.datatypes import (
    SAScheduleTupleEntry as SAScheduleTupleEntryDINSPEC,
)
from iso15118.shared.messages.enums import (
    Contactor,
    EnergyTransferModeEnum,
    IsolationLevel,
    PriceAlgorithm,
    Protocol,
    UnitSymbol,
)
from iso15118.shared.messages.iso15118_2.datatypes import (
    ACEVSEChargeParameter,
    ACEVSEStatus,
)
from iso15118.shared.messages.iso15118_2.datatypes import MeterInfo as MeterInfoV2
from iso15118.shared.messages.iso15118_2.datatypes import (
    PMaxSchedule,
    PMaxScheduleEntry,
    PVEVSEMaxCurrent,
    PVEVSENominalVoltage,
    PVPMax,
    RelativeTimeInterval,
    SalesTariff,
    SalesTariffEntry,
    SAScheduleTuple,
)
from iso15118.shared.messages.iso15118_20.ac import (
    ACChargeParameterDiscoveryResParams,
    BPTACChargeParameterDiscoveryResParams,
    BPTDynamicACChargeLoopResParams,
    BPTScheduledACChargeLoopResParams,
    DynamicACChargeLoopResParams,
    ScheduledACChargeLoopResParams,
)
from iso15118.shared.messages.iso15118_20.common_messages import (
    AbsolutePriceSchedule,
    AdditionalService,
    AdditionalServiceList,
    ChargingSchedule,
    DynamicScheduleExchangeResParams,
    OverstayRule,
    OverstayRuleList,
    PowerSchedule,
    PowerScheduleEntry,
    PowerScheduleEntryList,
    PriceLevelSchedule,
    PriceLevelScheduleEntry,
    PriceLevelScheduleEntryList,
    PriceRule,
    PriceRuleStack,
    PriceRuleStackList,
    ProviderID,
    ScheduledScheduleExchangeResParams,
    ScheduleExchangeReq,
    ScheduleTuple,
    SelectedEnergyService,
    Service,
    ServiceList,
    ServiceParameterList,
    TaxRule,
    TaxRuleList,
)
from iso15118.shared.messages.iso15118_20.common_types import (
    EVSENotification as EVSENotificationV20,
)
from iso15118.shared.messages.iso15118_20.common_types import EVSEStatus
from iso15118.shared.messages.iso15118_20.common_types import MeterInfo as MeterInfoV20
from iso15118.shared.messages.iso15118_20.common_types import RationalNumber
from iso15118.shared.messages.iso15118_20.dc import (
    BPTDCChargeParameterDiscoveryResParams,
    DCChargeParameterDiscoveryResParams,
)
from iso15118.shared.settings import V20_EVSE_SERVICES_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class EVDataContext:
    dc_current: Optional[int] = None
    dc_voltage: Optional[int] = None
    ac_current: Optional[dict] = None  # {"l1": 10, "l2": 10, "l3": 10}
    ac_voltage: Optional[dict] = None  # {"l1": 230, "l2": 230, "l3": 230}
    soc: Optional[int] = None  # 0-100


class V20ServiceParamMapping(BaseModel):
    service_id_parameter_set_mapping: dict[int, ServiceParameterList] = Field(
        ..., alias="service_id_parameter_set_mapping"
    )


# This method is added to help read the service to parameter
# mapping (json format) from file. The key is in the dictionary is
# enum value of the energy transfer mode and value is the service parameter
async def read_service_id_parameter_mappings():
    try:
        async with async_open(V20_EVSE_SERVICES_CONFIG, "r") as v20_service_config:
            try:
                json_mapping = await v20_service_config.read()
                v20_service_parameter_mapping = V20ServiceParamMapping.parse_raw(
                    json_mapping
                )
                return v20_service_parameter_mapping.service_id_parameter_set_mapping
            except ValueError as exc:
                raise ValueError(
                    f"Error reading 15118-20 service parameters settings file"
                    f" at {V20_EVSE_SERVICES_CONFIG}"
                ) from exc
    except (FileNotFoundError, IOError) as exc:
        raise FileNotFoundError(
            f"V20 config not found at {V20_EVSE_SERVICES_CONFIG}"
        ) from exc


class SimEVSEController(EVSEControllerInterface):
    """
    A simulated version of an EVSE controller
    """

    @classmethod
    async def create(cls):
        self = SimEVSEController()
        self.contactor = Contactor.OPENED
        self.ev_data_context = EVDataContext()
        self.v20_service_id_parameter_mapping = (
            await read_service_id_parameter_mappings()
        )
        return self

    def reset_ev_data_context(self):
        self.ev_data_context = EVDataContext()

    # ============================================================================
    # |             COMMON FUNCTIONS (FOR ALL ENERGY TRANSFER MODES)             |
    # ============================================================================

    def send_to_controller(self, stage: str, messages: bytes) -> bytes:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        if messages is None:
            messages = ""
        msg: dict = {
            'messages': messages,
            'stage': stage
        }
        socket.connect(os.environ.get('ZMQ_FOR_CP_AND_V2G'))
        socket.send(pickle.dumps(msg))
        rep = socket.recv()
        return rep

    # ============================================================================
    # |                          Dynamic by Controller                           |
    # ============================================================================
    # DONE : Implement the following functions By Controller
    def get_evse_id(self, protocol: Protocol) -> str:
        if protocol == Protocol.DIN_SPEC_70121:
            return pickle.loads(self.send_to_controller("get_evse_id", pickle.dumps({"protocol": "DIN"})))

        else:
            return pickle.loads(self.send_to_controller("get_evse_id", pickle.dumps({"protocol": "ISO15118"})))

    # ============================================================================
    # |                          Dynamic by Controller                           |
    # ============================================================================
    # DONE : Implement the following functions By Controller
    def get_supported_energy_transfer_modes(
            self, protocol: Protocol
    ) -> List[EnergyTransferModeEnum]:
        if protocol == Protocol.DIN_SPEC_70121:
            logger.info("get supported energy transfer mods DIN_SPEC_70121")
            return pickle.loads(
                self.send_to_controller("get_supported_energy_transfer_modes", pickle.dumps({"protocol": "DIN"})))

        else:
            logger.info("get supported energy transfer mods ISO15118")
            return pickle.loads(
                self.send_to_controller("get_supported_energy_transfer_modes", pickle.dumps({"protocol": "ISO15118"})))

    # TODO : Para #1
    def get_scheduled_se_params(
            self,
            selected_energy_service: SelectedEnergyService,
            schedule_exchange_req: ScheduleExchangeReq,
    ) -> Optional[ScheduledScheduleExchangeResParams]:
        """Overrides EVSEControllerInterface.get_scheduled_se_params()."""
        charging_power_schedule_entry = PowerScheduleEntry(
            duration=3600,
            power=RationalNumber(exponent=3, value=10)
            # Check if AC ThreePhase applies (Connector parameter within parameter set
            # of SelectedEnergyService) if you want to add power_l2 and power_l3 values
        )

        charging_power_schedule = PowerSchedule(
            time_anchor=0,
            available_energy=RationalNumber(exponent=3, value=300),
            power_tolerance=RationalNumber(exponent=0, value=2000),
            schedule_entry_list=PowerScheduleEntryList(
                entries=[charging_power_schedule_entry]
            ),
        )

        tax_rule = TaxRule(
            tax_rule_id=1,
            tax_rule_name="What a great tax rule",
            tax_rate=RationalNumber(exponent=0, value=10),
            tax_included_in_price=False,
            applies_to_energy_fee=True,
            applies_to_parking_fee=True,
            applies_to_overstay_fee=True,
            applies_to_min_max_cost=True,
        )

        tax_rules = TaxRuleList(tax_rule=[tax_rule])

        price_rule = PriceRule(
            energy_fee=RationalNumber(exponent=0, value=20),
            parking_fee=RationalNumber(exponent=0, value=0),
            parking_fee_period=0,
            carbon_dioxide_emission=0,
            renewable_energy_percentage=0,
            power_range_start=RationalNumber(exponent=0, value=0),
        )

        price_rule_stack = PriceRuleStack(duration=3600, price_rules=[price_rule])

        price_rule_stacks = PriceRuleStackList(price_rule_stacks=[price_rule_stack])

        overstay_rule = OverstayRule(
            description="What a great description",
            start_time=0,
            fee=RationalNumber(exponent=0, value=50),
            fee_period=3600,
        )

        overstay_rules = OverstayRuleList(
            time_threshold=3600,
            power_threshold=RationalNumber(exponent=3, value=30),
            rules=[overstay_rule],
        )

        additional_service = AdditionalService(
            service_name="What a great service name",
            service_fee=RationalNumber(exponent=0, value=0),
        )

        additional_services = AdditionalServiceList(
            additional_services=[additional_service]
        )

        charging_absolute_price_schedule = AbsolutePriceSchedule(
            time_anchor=0,
            schedule_id=1,
            currency="EUR",
            language="ENG",
            price_algorithm=PriceAlgorithm.POWER,
            min_cost=RationalNumber(exponent=0, value=1),
            max_cost=RationalNumber(exponent=0, value=10),
            tax_rules=tax_rules,
            price_rule_stacks=price_rule_stacks,
            overstay_rules=overstay_rules,
            additional_services=additional_services,
        )

        discharging_power_schedule_entry = PowerScheduleEntry(
            duration=3600,
            power=RationalNumber(exponent=3, value=10)
            # Check if AC ThreePhase applies (Connector parameter within parameter set
            # of SelectedEnergyService) if you want to add power_l2 and power_l3 values
        )

        discharging_power_schedule = PowerSchedule(
            time_anchor=0,
            schedule_entry_list=PowerScheduleEntryList(
                entries=[discharging_power_schedule_entry]
            ),
        )

        discharging_absolute_price_schedule = charging_absolute_price_schedule

        charging_schedule = ChargingSchedule(
            power_schedule=charging_power_schedule,
            absolute_price_schedule=charging_absolute_price_schedule,
        )

        discharging_schedule = ChargingSchedule(
            power_schedule=discharging_power_schedule,
            absolute_price_schedule=discharging_absolute_price_schedule,
        )

        schedule_tuple = ScheduleTuple(
            schedule_tuple_id=1,
            charging_schedule=charging_schedule,
            discharging_schedule=discharging_schedule,
        )

        scheduled_params = ScheduledScheduleExchangeResParams(
            schedule_tuples=[schedule_tuple]
        )

        return scheduled_params

    # TODO : Para #2
    def get_service_parameter_list(
            self, service_id: int
    ) -> Optional[ServiceParameterList]:
        """Overrides EVSEControllerInterface.get_service_parameter_list()."""
        if service_id in self.v20_service_id_parameter_mapping.keys():
            service_parameter_list = self.v20_service_id_parameter_mapping[service_id]
        else:
            logger.error(
                f"No ServiceParameterList available for service ID {service_id}"
            )
            return None

        return service_parameter_list

    # TODO : Para #3
    def get_dynamic_se_params(
            self,
            selected_energy_service: SelectedEnergyService,
            schedule_exchange_req: ScheduleExchangeReq,
    ) -> Optional[DynamicScheduleExchangeResParams]:
        """Overrides EVSEControllerInterface.get_dynamic_se_params()."""
        price_level_schedule_entry = PriceLevelScheduleEntry(
            duration=3600, price_level=1
        )

        schedule_entries = PriceLevelScheduleEntryList(
            entries=[price_level_schedule_entry]
        )

        price_level_schedule = PriceLevelSchedule(
            id="id1",
            time_anchor=0,
            schedule_id=1,
            schedule_description="What a great description",
            num_price_levels=1,
            schedule_entries=schedule_entries,
        )

        dynamic_params = DynamicScheduleExchangeResParams(
            departure_time=7200,
            min_soc=30,
            target_soc=80,
            price_level_schedule=price_level_schedule,
        )

        return dynamic_params

    # TODO : Para #4
    def get_energy_service_list(self) -> ServiceList:
        """Overrides EVSEControllerInterface.get_energy_service_list()."""
        # AC = 1, DC = 2, AC_BPT = 5, DC_BPT = 6;
        # DC_ACDP = 4 and DC_ADCP_BPT NOT supported
        service_ids = [1, 5]
        service_list: ServiceList = ServiceList(services=[])
        for service_id in service_ids:
            service_list.services.append(
                Service(service_id=service_id, free_service=False)
            )

        return service_list

    def is_authorised(self) -> bool:
        """Overrides EVSEControllerInterface.is_authorised()."""
        return pickle.loads(self.send_to_controller("is_authorised", pickle.dumps({"resp": "true"})))

    # TODO : Para #5
    def get_sa_schedule_list_dinspec(
            self, max_schedule_entries: Optional[int], departure_time: int = 0
    ) -> Optional[List[SAScheduleTupleEntryDINSPEC]]:
        """Overrides EVSEControllerInterface.get_sa_schedule_list_dinspec()."""
        sa_schedule_list: List[SAScheduleTupleEntryDINSPEC] = []
        entry_details = PMaxScheduleEntryDetailsDINSPEC(
            p_max=200, time_interval=RelativeTimeIntervalDINSPEC(start=0, duration=3600)
        )
        p_max_schedule_entries = [entry_details]
        pmax_schedule_entry = PMaxScheduleEntryDINSPEC(
            p_max_schedule_id=0, entry_details=p_max_schedule_entries
        )

        sa_schedule_tuple_entry = SAScheduleTupleEntryDINSPEC(
            sa_schedule_tuple_id=1,
            p_max_schedule=pmax_schedule_entry,
            sales_tariff=None,
        )
        sa_schedule_list.append(sa_schedule_tuple_entry)
        return sa_schedule_list

    # TODO : Para #6
    def get_sa_schedule_list(
            self, max_schedule_entries: Optional[int], departure_time: int = 0
    ) -> Optional[List[SAScheduleTuple]]:
        """Overrides EVSEControllerInterface.get_sa_schedule_list()."""
        sa_schedule_list: List[SAScheduleTuple] = []

        # PMaxSchedule
        p_max = PVPMax(multiplier=0, value=11000, unit=UnitSymbol.WATT)
        p_max_schedule_entry = PMaxScheduleEntry(
            p_max=p_max, time_interval=RelativeTimeInterval(start=0, duration=3600)
        )
        p_max_schedule = PMaxSchedule(schedule_entries=[p_max_schedule_entry])

        # SalesTariff
        sales_tariff_entries: List[SalesTariffEntry] = []
        sales_tariff_entry_1 = SalesTariffEntry(
            e_price_level=1, time_interval=RelativeTimeInterval(start=0)
        )
        sales_tariff_entry_2 = SalesTariffEntry(
            e_price_level=2,
            time_interval=RelativeTimeInterval(start=1801, duration=1799),
        )
        sales_tariff_entries.append(sales_tariff_entry_1)
        sales_tariff_entries.append(sales_tariff_entry_2)
        sales_tariff = SalesTariff(
            id="id1",
            sales_tariff_id=10,  # a random id
            sales_tariff_entry=sales_tariff_entries,
            num_e_price_levels=2,
        )

        # Putting the list of SAScheduleTuple entries together
        sa_schedule_tuple = SAScheduleTuple(
            sa_schedule_tuple_id=1,
            p_max_schedule=p_max_schedule,
            sales_tariff=sales_tariff,
        )

        # TODO We could also implement an optional SalesTariff, but for the sake of
        #      time we'll do that later (after the basics are implemented).
        #      When implementing the SalesTariff, we also need to apply a digital
        #      signature to it.
        sa_schedule_list.append(sa_schedule_tuple)

        # TODO We need to take care of [V2G2-741], which says that the SECC needs to
        #      resend a previously agreed SAScheduleTuple and the "period of time
        #      this SAScheduleTuple applies for shall be reduced by the time already
        #      elapsed".

        return sa_schedule_list

    # TODO : Para #7
    def get_meter_info_v2(self) -> MeterInfoV2:
        """Overrides EVSEControllerInterface.get_meter_info_v2()."""
        return MeterInfoV2(
            meter_id="Switch-Meter-123", meter_reading=12345, t_meter=time.time()
        )

    # TODO : v20 #1
    def get_meter_info_v20(self) -> MeterInfoV20:
        """Overrides EVSEControllerInterface.get_meter_info_v20()."""
        return MeterInfoV20(
            meter_id="Switch-Meter-123",
            charged_energy_reading_wh=10,
            meter_timestamp=time.time(),
        )

    # TODO : Check what is going on here #1
    def get_supported_providers(self) -> Optional[List[ProviderID]]:
        """Overrides EVSEControllerInterface.get_supported_providers()."""
        return None

    # TODO : Check what is going on here #2
    def set_hlc_charging(self, is_ongoing: bool) -> None:
        """Overrides EVSEControllerInterface.set_hlc_charging()."""
        pass

    def stop_charger(self) -> None:
        pass

    def service_renegotiation_supported(self) -> bool:
        """Overrides EVSEControllerInterface.service_renegotiation_supported()."""
        return False

    # Done : it's Chenged to get data from the controller
    def close_contactor(self):
        """Overrides EVSEControllerInterface.close_contactor()."""

        self.contactor = pickle.loads(self.send_to_controller("close_contactor", pickle.dumps({"state": "close"})))

    # Done : it's Chenged to get data from the controller
    def open_contactor(self):
        """Overrides EVSEControllerInterface.open_contactor()."""

        self.contactor = pickle.loads(self.send_to_controller("open_contactor", pickle.dumps({"state": "open"})))

    # Done : it's Chenged to get data from the controller
    def get_contactor_state(self) -> Contactor:
        """Overrides EVSEControllerInterface.get_contactor_state()."""
        return pickle.loads(self.send_to_controller("get_contactor_state", pickle.dumps({"state": "open"})))

    # changed to get data from controller
    def get_evse_status(self) -> EVSEStatus:
        return pickle.loads(self.send_to_controller('get_evse_status', pickle.dumps({'null': 'null'})))

    # Simple dummy function to get states
    def get_state(self, current: EVSEStatus) -> None:
        self.send_to_controller('get_state', pickle.dumps({'state': current}))

    # ============================================================================
    # |                          AC-SPECIFIC FUNCTIONS                           |
    # ============================================================================

    def get_ac_evse_status(self) -> ACEVSEStatus:
        """Overrides EVSEControllerInterface.get_ac_evse_status()."""
        return ACEVSEStatus(
            notification_max_delay=0,
            evse_notification=EVSENotificationV2.NONE,
            rcd=False,
        )

    def get_ac_charge_params_v2(self) -> ACEVSEChargeParameter:
        """Overrides EVSEControllerInterface.get_ac_evse_charge_parameter()."""
        evse_nominal_voltage = PVEVSENominalVoltage(
            multiplier=0, value=400, unit=UnitSymbol.VOLTAGE
        )
        evse_max_current = PVEVSEMaxCurrent(
            multiplier=0, value=32, unit=UnitSymbol.AMPERE
        )
        return ACEVSEChargeParameter(
            ac_evse_status=self.get_ac_evse_status(),
            evse_nominal_voltage=evse_nominal_voltage,
            evse_max_current=evse_max_current,
        )

    def get_ac_charge_params_v20(self) -> ACChargeParameterDiscoveryResParams:
        """Overrides EVSEControllerInterface.get_ac_charge_params_v20()."""
        return ACChargeParameterDiscoveryResParams(
            evse_max_charge_power=RationalNumber(exponent=3, value=11),
            evse_max_charge_power_l2=RationalNumber(exponent=3, value=11),
            evse_max_charge_power_l3=RationalNumber(exponent=3, value=11),
            evse_min_charge_power=RationalNumber(exponent=0, value=100),
            evse_min_charge_power_l2=RationalNumber(exponent=0, value=100),
            evse_min_charge_power_l3=RationalNumber(exponent=0, value=100),
            evse_nominal_frequency=RationalNumber(exponent=0, value=400),
            max_power_asymmetry=RationalNumber(exponent=0, value=500),
            evse_power_ramp_limit=RationalNumber(exponent=0, value=10),
            evse_present_active_power=RationalNumber(exponent=3, value=3),
            evse_present_active_power_l2=RationalNumber(exponent=3, value=3),
            evse_present_active_power_l3=RationalNumber(exponent=3, value=3),
        )

    def get_ac_bpt_charge_params_v20(self) -> BPTACChargeParameterDiscoveryResParams:
        """Overrides EVSEControllerInterface.get_ac_bpt_charge_params_v20()."""
        ac_charge_params_v20 = self.get_ac_charge_params_v20().dict()
        return BPTACChargeParameterDiscoveryResParams(
            **ac_charge_params_v20,
            evse_max_discharge_power=RationalNumber(exponent=0, value=3000),
            evse_max_discharge_power_l2=RationalNumber(exponent=0, value=3000),
            evse_max_discharge_power_l3=RationalNumber(exponent=0, value=3000),
            evse_min_discharge_power=RationalNumber(exponent=0, value=300),
            evse_min_discharge_power_l2=RationalNumber(exponent=0, value=300),
            evse_min_discharge_power_l3=RationalNumber(exponent=0, value=300),
        )

    def get_scheduled_ac_charge_loop_params(self) -> ScheduledACChargeLoopResParams:
        """Overrides EVControllerInterface.get_scheduled_ac_charge_loop_params()."""
        return ScheduledACChargeLoopResParams(
            evse_present_active_power=RationalNumber(exponent=3, value=3),
            evse_present_active_power_l2=RationalNumber(exponent=3, value=3),
            evse_present_active_power_l3=RationalNumber(exponent=3, value=3),
            # Add more optional fields if wanted
        )

    def get_bpt_scheduled_ac_charge_loop_params(
            self,
    ) -> BPTScheduledACChargeLoopResParams:
        """Overrides EVControllerInterface.get_bpt_scheduled_ac_charge_loop_params()."""
        return BPTScheduledACChargeLoopResParams(
            evse_present_active_power=RationalNumber(exponent=3, value=3),
            evse_present_active_power_l2=RationalNumber(exponent=3, value=3),
            evse_present_active_power_l3=RationalNumber(exponent=3, value=3),
            # Add more optional fields if wanted
        )

    def get_dynamic_ac_charge_loop_params(self) -> DynamicACChargeLoopResParams:
        """Overrides EVControllerInterface.get_dynamic_ac_charge_loop_params()."""
        return DynamicACChargeLoopResParams(
            evse_target_active_power=RationalNumber(exponent=3, value=3),
            evse_target_active_power_l2=RationalNumber(exponent=3, value=3),
            evse_target_active_power_l3=RationalNumber(exponent=3, value=3),
            # Add more optional fields if wanted
        )

    def get_bpt_dynamic_ac_charge_loop_params(self) -> BPTDynamicACChargeLoopResParams:
        """Overrides EVControllerInterface.get_bpt_dynamic_ac_charge_loop_params()."""
        return BPTDynamicACChargeLoopResParams(
            evse_target_active_power=RationalNumber(exponent=3, value=3),
            evse_target_active_power_l2=RationalNumber(exponent=3, value=3),
            evse_target_active_power_l3=RationalNumber(exponent=3, value=3),
            # Add more optional fields if wanted
        )

    # ============================================================================
    # |                          DC-SPECIFIC FUNCTIONS                           |
    # ============================================================================

    # changed to get_dc_evse_status get from the controller
    def get_dc_evse_status(self) -> DCEVSEStatus:
        """Overrides EVSEControllerInterface.get_dc_evse_status()."""
        return pickle.loads(self.send_to_controller('get_dc_evse_status', pickle.dumps({'null': 'null'})))

    # changed to get data from the controller
    def get_dc_evse_charge_parameter(self) -> DCEVSEChargeParameter:
        """Overrides EVSEControllerInterface.get_dc_evse_charge_parameter()."""
        return pickle.loads(self.send_to_controller('get_dc_evse_charge_parameter', pickle.dumps({'null': 'null'})))

    # changed to get data from the controller
    def get_evse_present_voltage(self) -> PVEVSEPresentVoltage:
        """Overrides EVSEControllerInterface.get_evse_present_voltage()."""
        return pickle.loads(self.send_to_controller('get_evse_present_voltage', pickle.dumps({'null': 'null'})))

    # changed to get data from the controller
    def get_evse_present_current(self) -> PVEVSEPresentCurrent:
        """Overrides EVSEControllerInterface.get_evse_present_current()."""
        return pickle.loads(self.send_to_controller('get_evse_present_current', pickle.dumps({'null': 'null'})))

    # TODO: implement start_cable_check()
    def start_cable_check(self):
        self.send_to_controller('start_cable_check', pickle.dumps({'null': 'null'}))

    # TODO: implement set_precharge()
    def set_precharge(self, voltage: PVEVTargetVoltage, current: PVEVTargetCurrent):
        self.send_to_controller('set_precharge', pickle.dumps({'voltage': voltage, 'current': current}))

    # TODO: implement send_charging_command()
    def send_charging_command(
            self, voltage: PVEVTargetVoltage, current: PVEVTargetCurrent
    ):
        self.send_to_controller('send_charging_command', pickle.dumps({'voltage': voltage, 'current': current,
                                                                       'soc': EVDataContext.soc}))

    # changed to get data from the controller
    def is_evse_current_limit_achieved(self) -> bool:
        return pickle.loads(self.send_to_controller('is_evse_current_limit_achieved', pickle.dumps({"null": "null"})))

    # changed to get data from controller
    def is_evse_voltage_limit_achieved(self) -> bool:
        return pickle.loads(self.send_to_controller('is_evse_voltage_limit_achieved', pickle.dumps({"null": "null"})))

    # changed to get data from controller
    def is_evse_power_limit_achieved(self) -> bool:
        return pickle.loads(self.send_to_controller('is_evse_power_limit_achieved', pickle.dumps({"null": "null"})))

    # changed to get data from the controller
    def get_evse_max_voltage_limit(self) -> PVEVSEMaxVoltageLimit:
        return pickle.loads(self.send_to_controller('get_evse_max_voltage_limit', pickle.dumps({"null": "null"})))

    # changed to get data from the controller
    def get_evse_max_current_limit(self) -> PVEVSEMaxCurrentLimit:
        return pickle.loads(self.send_to_controller('get_evse_max_current_limit', pickle.dumps({"null": "null"})))

    # changed to get data from the controller
    def get_evse_max_power_limit(self) -> PVEVSEMaxPowerLimit:
        return pickle.loads(self.send_to_controller('get_evse_max_power_limit', pickle.dumps({"null": "null"})))

    # changed to get data from the controller
    def get_dc_charge_params_v20(self) -> DCChargeParameterDiscoveryResParams:
        """Overrides EVSEControllerInterface.get_dc_charge_params_v20()."""
        return pickle.loads(self.send_to_controller('get_dc_charge_params_v20', pickle.dumps({"null": "null"})))

    # changed to get data from the controller
    def get_dc_bpt_charge_params_v20(self) -> BPTDCChargeParameterDiscoveryResParams:
        """Overrides EVSEControllerInterface.get_dc_bpt_charge_params_v20()."""
        return pickle.loads(self.send_to_controller('get_dc_bpt_charge_params_v20', pickle.dumps({"null": "null"})))
