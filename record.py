import os
import pandas as pd

# Translation mapping dictionaries for column headers
COLUMN_TRANSLATIONS = {
    # Trades
    "交易日": "Trading Day",
    "交易阶段": "Trading Session",
    "股票类型": "Stock Symbol",
    "买入交易员": "Buyer Trader ID",
    "卖出交易员": "Seller Trader ID",
    "交易数量": "Trade Quantity",
    "交易价格": "Trade Price",

    # Stocks
    "第几个交易阶段": "Trading Session",
    "阶段结束后股票A价格": "Stock A Close Price",
    "阶段结束后股票B价格": "Stock B Close Price",

    # Daily Agent Records
    "交易员": "Trader ID",
    "是否贷款": "Loan Requested",
    "贷款类型": "Loan Type",
    "贷款数量": "Loan Amount",
    "明日是否贷款": "Next Day Loan Forecast",
    "明日是否买入A": "Next Day Buy A Forecast",
    "明日是否卖出A": "Next Day Sell A Forecast",
    "明日是否买入B": "Next Day Buy B Forecast",
    "明日是否卖出B": "Next Day Sell B Forecast",

    # Session Agent Records
    "交易前资产总额": "Total Assets Before Trading",
    "交易前持有现金": "Cash Before Trading",
    "交易前持有的A股价值": "Stock A Value Before Trading",
    "交易前持有的B股价值": "Stock B Value Before Trading",
    "挂单类型": "Order Type",
    "挂单股票类别": "Order Stock Symbol",
    "挂单数量": "Order Quantity",
    "挂单价格": "Order Price",
}

VALUE_TRANSLATIONS = {
    "买入": "buy",
    "卖出": "sell",
    "买": "buy",
    "卖": "sell",
    "是": "yes",
    "否": "no",
    "有": "yes",
    "无": "no",
    "不交易": "no",
    "A股": "A",
    "B股": "B",
    "股票A": "A",
    "股票B": "B",
}

DEFAULT_SHEET_NAMES = {
    "trades.xlsx": "Trade Records",
    "stocks.xlsx": "Stock Prices",
    "agent_day_record.xlsx": "Daily Records",
    "agent_session_record.xlsx": "Session Records",
}


def translate_value(val):
    if not isinstance(val, str):
        return val
    cleaned = val.strip()
    if cleaned in VALUE_TRANSLATIONS:
        return VALUE_TRANSLATIONS[cleaned]
    res = val
    for zh, en in VALUE_TRANSLATIONS.items():
        if zh in res:
            res = res.replace(zh, en)
    return res


def translate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    # Rename column headers
    df = df.rename(columns=lambda c: COLUMN_TRANSLATIONS.get(str(c).strip(), str(c).strip()))
    # Translate cell values
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].apply(translate_value)
    return df


def ensure_excel_english(file_name: str):
    """Inspect and convert an Excel file to ensure all columns, values, and sheet names are in English."""
    if not os.path.isfile(file_name):
        return
    base_name = os.path.basename(file_name)
    default_sheet = DEFAULT_SHEET_NAMES.get(base_name, "Sheet1")
    try:
        xls = pd.ExcelFile(file_name)
        sheets = {}
        for s in xls.sheet_names:
            df = pd.read_excel(file_name, sheet_name=s)
            df = translate_dataframe(df)
            new_sheet_name = default_sheet if (s.startswith("Sheet") or any(ord(c) > 127 for c in s)) else s
            sheets[new_sheet_name] = df

        with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
            for s_name, s_df in sheets.items():
                s_df.to_excel(writer, sheet_name=s_name, index=False)
    except Exception as e:
        print(f"Error ensuring English for {file_name}: {e}")


# Trade Execution Records
class TradeRecord:
    COLUMNS = [
        "Trading Day",
        "Trading Session",
        "Stock Symbol",
        "Buyer Trader ID",
        "Seller Trader ID",
        "Trade Quantity",
        "Trade Price",
    ]

    def __init__(self, date, session, stock_type, buyer, seller, quantity, price):
        self.date = date
        self.session = session
        self.stock_type = stock_type
        self.buyer = buyer
        self.seller = seller
        self.quantity = quantity
        self.price = price

    def write_to_excel(self, file_name="res/trades.xlsx"):
        os.makedirs(os.path.dirname(file_name) or ".", exist_ok=True)
        if os.path.isfile(file_name):
            try:
                existing_df = pd.read_excel(file_name)
                existing_df = translate_dataframe(existing_df)
            except Exception:
                existing_df = pd.DataFrame(columns=self.COLUMNS)
        else:
            existing_df = pd.DataFrame(columns=self.COLUMNS)

        new_records = [[
            self.date,
            self.session,
            translate_value(str(self.stock_type)),
            self.buyer,
            self.seller,
            self.quantity,
            self.price,
        ]]
        new_df = pd.DataFrame(new_records, columns=self.COLUMNS)
        all_records_df = pd.concat([existing_df, new_df], ignore_index=True)
        all_records_df = translate_dataframe(all_records_df)
        all_records_df.to_excel(file_name, sheet_name="Trade Records", index=False)


def create_trade_record(date, stage, stock, buy_trader, sell_trader, amount, price):
    record = TradeRecord(date, stage, stock, buy_trader, sell_trader, amount, price)
    record.write_to_excel()
    record = None


# Stock Price Records
class StockRecord:
    COLUMNS = [
        "Trading Day",
        "Trading Session",
        "Stock A Close Price",
        "Stock B Close Price",
    ]

    def __init__(self, date, session, stock_a_price, stock_b_price):
        self.date = date
        self.session = session
        self.stock_a_price = stock_a_price
        self.stock_b_price = stock_b_price

    def write_to_excel(self, file_name="res/stocks.xlsx"):
        os.makedirs(os.path.dirname(file_name) or ".", exist_ok=True)
        if os.path.isfile(file_name):
            try:
                existing_df = pd.read_excel(file_name)
                existing_df = translate_dataframe(existing_df)
            except Exception:
                existing_df = pd.DataFrame(columns=self.COLUMNS)
        else:
            existing_df = pd.DataFrame(columns=self.COLUMNS)

        new_records = [[self.date, self.session, self.stock_a_price, self.stock_b_price]]
        new_df = pd.DataFrame(new_records, columns=self.COLUMNS)
        all_records_df = pd.concat([existing_df, new_df], ignore_index=True)
        all_records_df = translate_dataframe(all_records_df)
        all_records_df.to_excel(file_name, sheet_name="Stock Prices", index=False)


def create_stock_record(date, session, stock_a_price, stock_b_price):
    record = StockRecord(date, session, stock_a_price, stock_b_price)
    record.write_to_excel()
    record = None


# Daily Agent Loan & Forecast Records
class AgentRecordDaily:
    COLUMNS = [
        "Trader ID",
        "Trading Day",
        "Loan Requested",
        "Loan Type",
        "Loan Amount",
        "Next Day Loan Forecast",
        "Next Day Buy A Forecast",
        "Next Day Sell A Forecast",
        "Next Day Buy B Forecast",
        "Next Day Sell B Forecast",
    ]

    def __init__(self, agent, date, loan_json=None):
        if hasattr(agent, "order"):
            agent = agent.order
        if hasattr(date, "order"):
            agent, date = date.order, agent
        self.agent = agent
        self.date = date
        self.if_loan = "no"
        self.loan_type = 0
        self.loan_amount = 0.0
        if isinstance(loan_json, dict):
            self.if_loan = translate_value(str(loan_json.get("loan", "no"))).lower()
            if self.if_loan == "yes":
                self.loan_type = loan_json.get("loan_type", 0)
                self.loan_amount = loan_json.get("amount", 0.0)
        self.will_loan = "no"
        self.will_buy_a = "no"
        self.will_sell_a = "no"
        self.will_buy_b = "no"
        self.will_sell_b = "no"

    def add_estimate(self, js):
        if isinstance(js, dict):
            self.will_loan = translate_value(str(js.get("loan", "no"))).lower()
            self.will_buy_a = translate_value(str(js.get("buy_A", "no"))).lower()
            self.will_sell_a = translate_value(str(js.get("sell_A", "no"))).lower()
            self.will_buy_b = translate_value(str(js.get("buy_B", "no"))).lower()
            self.will_sell_b = translate_value(str(js.get("sell_B", "no"))).lower()

    def write_to_excel(self, file_name="res/agent_day_record.xlsx"):
        os.makedirs(os.path.dirname(file_name) or ".", exist_ok=True)
        if os.path.isfile(file_name):
            try:
                existing_df = pd.read_excel(file_name)
                existing_df = translate_dataframe(existing_df)
            except Exception:
                existing_df = pd.DataFrame(columns=self.COLUMNS)
        else:
            existing_df = pd.DataFrame(columns=self.COLUMNS)

        new_records = [[
            self.agent,
            self.date,
            self.if_loan,
            self.loan_type,
            self.loan_amount,
            self.will_loan,
            self.will_buy_a,
            self.will_sell_a,
            self.will_buy_b,
            self.will_sell_b,
        ]]
        new_df = pd.DataFrame(new_records, columns=self.COLUMNS)
        all_records_df = pd.concat([existing_df, new_df], ignore_index=True)
        all_records_df = translate_dataframe(all_records_df)
        all_records_df.to_excel(file_name, sheet_name="Daily Records", index=False)


# Trading Session Agent Status & Order Records
class AgentRecordSession:
    COLUMNS = [
        "Trader ID",
        "Trading Day",
        "Trading Session",
        "Total Assets Before Trading",
        "Cash Before Trading",
        "Stock A Value Before Trading",
        "Stock B Value Before Trading",
        "Order Type",
        "Order Stock Symbol",
        "Order Quantity",
        "Order Price",
    ]

    def __init__(self, agent, date, session, proper, cash, stock_a_value, stock_b_value, action_json=None):
        if hasattr(agent, "order"):
            agent = agent.order
        self.agent = agent
        self.date = date
        self.session = session
        self.proper = proper
        self.cash = cash
        self.stock_a_value = stock_a_value
        self.stock_b_value = stock_b_value
        self.action_stock = "-"
        self.amount = 0
        self.price = 0.0
        self.action_type = "no"
        if isinstance(action_json, dict):
            self.action_type = translate_value(str(action_json.get("action_type", "no"))).lower()
            if self.action_type != "no":
                self.action_stock = translate_value(str(action_json.get("stock", "-")))
                self.amount = action_json.get("amount", 0)
                self.price = action_json.get("price", 0.0)

    def write_to_excel(self, file_name="res/agent_session_record.xlsx"):
        os.makedirs(os.path.dirname(file_name) or ".", exist_ok=True)
        if os.path.isfile(file_name):
            try:
                existing_df = pd.read_excel(file_name)
                existing_df = translate_dataframe(existing_df)
            except Exception:
                existing_df = pd.DataFrame(columns=self.COLUMNS)
        else:
            existing_df = pd.DataFrame(columns=self.COLUMNS)

        new_records = [[
            self.agent,
            self.date,
            self.session,
            self.proper,
            self.cash,
            self.stock_a_value,
            self.stock_b_value,
            self.action_type,
            self.action_stock,
            self.amount,
            self.price,
        ]]
        new_df = pd.DataFrame(new_records, columns=self.COLUMNS)
        all_records_df = pd.concat([existing_df, new_df], ignore_index=True)
        all_records_df = translate_dataframe(all_records_df)
        all_records_df.to_excel(file_name, sheet_name="Session Records", index=False)


def create_agentses_record(agent, date, session, proper, cash, stock_a_value, stock_b_value, action_json):
    record = AgentRecordSession(agent, date, session, proper, cash, stock_a_value, stock_b_value, action_json)
    record.write_to_excel()
    record = None
