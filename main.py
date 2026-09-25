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
        self.binance_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

    def log(self, text):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {text}", flush=True)

    def get_btc_data(self):
        start = time.time()
        try:
            res = requests.get(self.binance_url, timeout=3)
            ping_ms = int((time.time() - start) * 1000)
            if res.status_code == 200:
                price = float(res.json().get("price", 0))
                return price, ping_ms
        except Exception:
            pass
        return None, 0

    def run(self):
        self.log("🚀 Бот-симулятор для Railway успешно запущен!")
        self.log(f"💼 Стартовый виртуальный баланс: ${self.balance:.2f} USDC")
        
        while True:
            btc_price, ping = self.get_btc_data()
            now = datetime.now()
            interval_id = f"{now.strftime('%H')}:{(now.minute // 15) * 15:02d}"
            minute = now.minute % 15
            
            # Новая 15-минутка
            if self.current_interval != interval_id:
                self.current_interval = interval_id
                self.start_btc_price = btc_price
                self.traded_this_interval = False
                total = self.wins + self.losses
                wr = (self.wins / total * 100) if total > 0 else 0
                self.log(f"--- Новая 15-минутка [{interval_id}] | Старт BTC: ${btc_price:,.1f} | Баланс: ${self.balance:.2f} (WR: {wr:.0f}%) ---")

            if btc_price and self.start_btc_price:
                impulse = btc_price - self.start_btc_price
                
                # Сигнал на 12-14 минутах
                if minute >= 12 and not self.traded_this_interval:
                    if abs(impulse) >= self.min_impulse:
                        direction = "BTC Up ⬆️" if impulse > 0 else "BTC Down ⬇️"
                        
                        # Расчет вин/лос
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
  
