import requests
import time
from datetime import datetime

class PolyBotRailway:
    def __init__(self, initial_balance=15.0):
        self.balance = initial_balance
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0
        self.trade_amount = 1.50
        self.min_impulse = 80.0
        
        self.start_btc_price = None
        self.current_interval = None
        self.traded_this_interval = False
        self.last_heartbeat = 0

    def log(self, text):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {text}", flush=True)

    def get_btc_price(self):
        """Получение цены BTC из нескольких источников (для обхода блокировок облачных IP)"""
        sources = [
            # Bybit
            ("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", 
             lambda r: float(r.json()["result"]["list"][0]["lastPrice"])),
            # Coinbase
            ("https://api.coinbase.com/v2/prices/BTC-USD/spot", 
             lambda r: float(r.json()["data"]["amount"])),
            # Binance US
            ("https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT", 
             lambda r: float(r.json()["price"])),
            # Binance Global
            ("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", 
             lambda r: float(r.json()["price"])),
            # OKX
            ("https://api.okx.com/api/v5/market/ticker?instId=BTC-USDT", 
             lambda r: float(r.json()["data"][0]["last"]))
        ]

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        for url, parser in sources:
            try:
                res = requests.get(url, headers=headers, timeout=3)
                if res.status_code == 200:
                    price = parser(res)
                    if price > 0:
                        return price
            except Exception:
                continue

        return None

    def run(self):
        self.log("🚀 Бот-симулятор для Railway успешно запущен!")
        self.log(f"💼 Стартовый виртуальный баланс: ${self.balance:.2f} USDC")
        
        err_count = 0

        while True:
            btc_price = self.get_btc_price()
            now = datetime.now()
            interval_id = f"{now.strftime('%H')}:{(now.minute // 15) * 15:02d}"
            minute = now.minute % 15
            
            # Если цена не подгрузилась
            if btc_price is None:
                err_count += 1
                if err_count % 6 == 1:
                    self.log("⚠️ Не удалось получить цену BTC (повторная попытка через 5 сек)...")
                time.sleep(5)
                continue
            else:
                err_count = 0

            # Первый запуск
            if self.current_interval is None:
                self.current_interval = interval_id
                self.start_btc_price = btc_price
                self.traded_this_interval = False
                self.log(f"📍 Старт отслеживания | Интервал [{interval_id}] | BTC: ${btc_price:,.1f}")

            # Новая 15-минутка
            elif self.current_interval != interval_id:
                self.current_interval = interval_id
                self.start_btc_price = btc_price
                self.traded_this_interval = False
                total = self.wins + self.losses
                wr = (self.wins / total * 100) if total > 0 else 0
                self.log(f"--- Новая 15-минутка [{interval_id}] | Старт BTC: ${btc_price:,.1f} | Баланс: ${self.balance:.2f} (WR: {wr:.0f}%) ---")

            impulse = btc_price - self.start_btc_price if self.start_btc_price else 0.0

            # Пульс каждые 60 секунд
            if time.time() - self.last_heartbeat >= 60:
                self.last_heartbeat = time.time()
                self.log(f"👀 Мониторинг [{interval_id}] (мин {minute:02d}/15) | BTC: ${btc_price:,.1f} | Импульс: ${impulse:+.1f} / ${self.min_impulse:.0f}")

            # Проверка сигнала на 12-14 минутах
            if minute >= 12 and not self.traded_this_interval:
                if abs(impulse) >= self.min_impulse:
                    direction = "BTC Up ⬆️" if impulse > 0 else "BTC Down ⬇️"
                    
                    pnl = 0.37 if impulse != 0 else -1.50
                    if pnl > 0:
                        self.wins += 1
                        res_text = "WIN 🟢 (+ $0.37)"
                    else:
                        self.losses += 1
                        res_text = "LOSS 🔴 (- $1.50)"
                        
                    self.balance += pnl
                    self.total_pnl += pnl
                    self.traded_this_interval = True
                    
                    self.log(f"🔥 СДЕЛКА! Направление: {direction} | BTC: ${btc_price:,.1f} | Импульс: ${impulse:+.1f}")
                    self.log(f"📊 Результат: {res_text} | Новый баланс: ${self.balance:.2f}")

            time.sleep(10)

if __name__ == "__main__":
    bot = PolyBotRailway(15.0)
    bot.run()
    
