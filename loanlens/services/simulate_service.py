from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from loanlens.config import AppConfig
from loanlens.engine.schedule import generate_schedule
from loanlens.engine.simulate import (
    compare_prepay_vs_invest,
    simulate_prepayment,
    simulate_rate_change,
    simulate_recurring,
)
from loanlens.models import (
    CompareResult,
    LoanProfile,
    ScheduleRow,
    SimulationOutput,
    SimulationResult,
)
from loanlens.store.base import StoreBase


class SimulateService:
    def __init__(self, store: StoreBase, config: AppConfig) -> None:
        self._store = store
        self._config = config

    def _loan_and_schedule(self, loan_id: UUID) -> tuple[LoanProfile, list[ScheduleRow]]:
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        schedule = self._store.get_schedule(loan_id)
        if not schedule:
            schedule = generate_schedule(
                loan,
                self._store.list_rate_revisions(loan_id),
                self._store.list_moratoriums(loan_id),
                self._store.list_payments(loan_id),
                [],
                self._config,
            )
            self._store.save_schedule(loan_id, schedule)
        return loan, schedule

    def prepay(
        self,
        loan_id: UUID,
        prepayment_amount: Decimal,
        prepayment_date: date,
        mode: str,
        include_charges: bool,
    ) -> SimulationOutput:
        loan, schedule = self._loan_and_schedule(loan_id)
        return simulate_prepayment(
            loan,
            schedule,
            prepayment_amount,
            prepayment_date,
            mode,
            include_charges,
            self._config,
        )

    def recurring(
        self,
        loan_id: UUID,
        monthly_amount: Decimal,
        start_date: date,
        mode: str,
    ) -> SimulationOutput:
        loan, schedule = self._loan_and_schedule(loan_id)
        return simulate_recurring(loan, schedule, monthly_amount, start_date, mode, self._config)

    def rate_change(
        self,
        loan_id: UUID,
        new_roi: Decimal,
        effective_date: date,
        mode: str,
    ) -> SimulationOutput:
        loan, schedule = self._loan_and_schedule(loan_id)
        return simulate_rate_change(loan, schedule, new_roi, effective_date, mode, self._config)

    def compare(
        self,
        loan_id: UUID,
        prepayment_amount: Decimal,
        prepayment_date: date,
        mode: str,
        invest_return_pct: Decimal,
    ) -> CompareResult:
        prepay_result = self.prepay(loan_id, prepayment_amount, prepayment_date, mode, False)
        return compare_prepay_vs_invest(
            prepayment_amount,
            prepay_result.interest_saved,
            prepay_result.months_saved,
            invest_return_pct,
        )

    def save(
        self,
        loan_id: UUID,
        simulation_type: str,
        inputs: dict[str, object],
        output: SimulationOutput,
        label: str = "",
    ) -> SimulationResult:
        result = SimulationResult(
            loan_id=loan_id,
            simulation_type=simulation_type,
            inputs=inputs,
            outputs={
                "months_saved": output.months_saved,
                "interest_saved": str(output.interest_saved),
                "new_emi": str(output.new_emi),
                "new_closure_date": output.new_closure_date.isoformat()
                if output.new_closure_date is not None
                else None,
                "effective_yield_pct": str(output.effective_yield_pct),
            },
            revised_schedule=output.revised_schedule,
            label=label,
        )
        self._store.save_simulation(result)
        return result

    def get(self, simulation_id: UUID) -> SimulationResult | None:
        return self._store.get_simulation(simulation_id)

    def list(self, loan_id: UUID) -> list[SimulationResult]:
        return self._store.list_simulations(loan_id)
