from engine.types import LoanData, OdSavingsData, OdBalanceLog

def sync_od_balance_log(loan_data: LoanData, od_data: OdSavingsData) -> None:
    events = []
    
    for c in od_data.contributions:
        events.append({"date": c.date, "amount": float(c.amount), "id": c.id})
        
    for p in loan_data.paymentLog:
        if p.amountPaid > 0:
            d = p.paidDate if p.paidDate else p.dueDate
            events.append({"date": d, "amount": -float(p.amountPaid), "id": p.id})
            
    # Sort events. If same date, positive amounts (contributions) before negative (EMIs)
    events.sort(key=lambda e: (e["date"], -e["amount"]))
    
    balance = 0.0
    log_map = {}
    
    for e in events:
        balance += e["amount"]
        balance = max(0.0, balance)
        log_map[e["date"]] = balance
        
    new_logs = []
    for date, bal in log_map.items():
        log_id = f"auto_{date.replace('-', '')}"
        new_logs.append(OdBalanceLog(id=log_id, date=date, balance=bal))
        
    loan_data.odBalanceLog = new_logs
    od_data.odBalanceAnnotations = []
