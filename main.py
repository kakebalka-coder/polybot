import os
import json
import requests
import time
import threading
from datetime import datetime

STATE_FILE = "state.json"

class PolyBotRailway:
    def __init__(self, initial_balance=15.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.peak_balance = initial_balance
        self.max_drawdown_pct = 0.0
        
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0
        self.api_errors = 0
        
        self.cur_win_streak = 0
        self.max_win_streak = 0
        self.cur_loss_streak = 0
        self.max_loss_streak = 0
        
        self.min_impulse = 80.0
        self.win_impulses = []
        self.loss_impulses = []
        self.trade_history = []
        
        self.start_btc_price = None
        self.current_interval = None
        self.active_trade = None
        self.last_heartbeat = 0
        self.last_update_id = 0

        self.tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        # Загрузка сохраненного состояния при старте
        self.load_state()

    def save_state(self):
        """Сохранение статистики в файл для защиты от перезапусков"""
        data = {
            "balance": self.balance,
            "peak_balance": self.peak_balance,
            "max_drawdown_pct": self.max_drawdown_pct,
            "total_pnl": self.total_pnl,
            "wins": self.wins,
            "losses": self.losses,
            "cur_win_streak": self.cur_win_streak,
            "max_win_streak": self.max_win_streak,
            "cur_loss_streak": self.cur_loss_streak,
            "max_loss_streak": self.max_loss_streak,
            "win_impulses": self.win_impulses,
            "loss_impulses": self.loss_impulses,
            "trade_history": self.trade_history
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"⚠️ Ошибка сохранения состояния: {e}")

    def load_state(self):
        """Восстановление статистики из файла"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.balance = data.get("balance", self.initial_balance)
                    self.peak_balance = data.get("peak_balance", self.initial_balance)
                    self.max_drawdown_pct = data.get("max_drawdown_pct", 0.0)
                    self.total_pnl = data.get("total_pnl", 0.0)
                    self.wins = data.get("wins", 0)
                    self.losses = data.get("losses", 0)
                    self.cur_win_streak = data.get("cur_win_streak", 0)
                    self.max_win_streak = data.get("max_win_streak", 0)
                    self.cur_loss_streak = data.get("cur_loss_streak", 0)
                    self.max_loss_streak = data.get("max_loss_streak", 0)
                    self.win_impulses = data.get("win_impulses", [])
                    self.loss_impulses = data.get("loss_impulses", [])
                    self.trade_history = data.get("trade_history", [])
                    self.log(f"💾 Данные восстановлены! Баланс: ${self.balance:.2f} | Сделок: {self.wins + self.losses}")
            except Exception as e:
                self.log(f"⚠️ Ошибка загрузки состояния: {e}")

    def log(self, text):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {text}", flush=True)

    def send_telegram(self, text):
        if not self.tg_token or not self.tg_chat_id:
            return
        
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        payload = {"chat_id": self.tg_chat_id, "text": text, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            self.log(f"⚠️ Ошибка отправки в Telegram: {e}")

    def get_analytics_text(self):
        total_trades = self.wins + self.losses
        winrate = (self.wins / total_trades * 100) if total_trades > 0 else 0.0
        avg_win_impulse = sum(self.win_impulses) / len(self.win_impulses) if self.win_impulses else 0.0
        avg_loss_impulse = sum(self.loss_impulses) / len(self.loss_impulses) if self.loss_impulses else 0.0
        roi_pct = ((self.balance - self.initial_balance) / self.initial_balance) * 100

        return (
            f"📊 <b>[ОТЧЕТ ПО СТРАТЕГИИ]</b>\n\n"
            f"💰 <b>Баланс:</b> ${self.balance:.2f} (PnL: {roi_pct:+.2f}%)\n"
            f"🎯 <b>Сделок:</b> {total_trades} | <b>WIN:</b> {self.wins} | <b>LOSS:</b> {self.losses}\n"
            f"🔥 <b>Винрейт:</b> {winrate:.2f}% (Порог: 80.2%)\n"
            f"📉 <b>Макс. просадка:</b> -{self.max_drawdown_pct:.2f}%\n"
            f"🏆 <b>Серии:</b> WIN = {self.max_win_streak} | LOSS = {self.max_loss_streak}\n"
            f"⚡ <b>Ср. импульс:</b> WIN=${avg_win_impulse:.1f} | LOSS=${avg_loss_impulse:.1f}"
        )

    def get_diagnostic_text(self):
        total_trades = self.wins + self.losses
        winrate = (self.wins / total_trades * 100) if total_trades > 0 else 0.0
        avg_win = sum(self.win_impulses) / len(self.win_impulses) if self.win_impulses else 0.0
        avg_loss = sum(self.loss_impulses) / len(self.loss_impulses) if self.loss_impulses else 0.0
        diff_impulse = avg_win - avg_loss
        
        recommendation = "Параметры оптимальны."
        if avg_loss > 0 and avg_loss < 90:
            recommendation = "Рекомендуется поднять порог импульса до $90–$100 для отсечения шума."

        return (
            f"🛠 <b>[ГЛУБОКАЯ ДИАГНОСТИКА]</b>\n\n"
            f"🔹 <b>Сделок:</b> {total_trades} | <b>Винрейт:</b> {winrate:.2f}%\n"
            f"🔹 <b>Ср. импульс WIN:</b> ${avg_win:.1f}\n"
            f"🔹 <b>Ср. импульс LOSS:</b> ${avg_loss:.1f}\n"
            f"🔹 <b>Дельта импульсов:</b> ${diff_impulse:+.1f}\n"
            f"🔹 <b>Сбоев API:</b> {self.api_errors}\n\n"
            f"💡 <b>Рекомендация:</b> {recommendation}"
        )

    def get_history_text(self):
        if not self.trade_history:
            return "📜 <b>История сделок пока пуста.</b>"
        
        text = "📜 <b>[ПОСЛЕДНИЕ СДЕЛКИ]</b>\n\n"
        for t in self.trade_history[-5:]:
            icon = "🟢" if t["is_win"] else "🔴"
            text += (
                f"{icon} <b>{t['interval']}</b>: {t['direction']} | "
                f"Вход: ${t['entry']:,.1f} ➔ Выход: ${t['exit']:,.1f} | "
                f"Импульс: ${t['impulse']:+.1f}\n"
            )
        return text

    def process_telegram_command(self, text):
        cmd = text.strip().lower()
        if cmd in ["/start", "/help"]:
            msg = (
                "🤖 <b>Команды бота:</b>\n\n"
                "/stats — Баланс и статистика\n"
                "/diag — Диагностика стратегии\n"
                "/history — История сделок\n"
                "/help — Справка"
            )
            self.send_telegram(msg)
        elif cmd == "/stats":
            self.send_telegram(self.get_analytics_text())
        elif cmd == "/diag":
            self.send_telegram(self.get_diagnostic_text())
        elif cmd == "/history":
            self.send_telegram(self.get_history_text())

    def start_telegram_listener(self):
        def listen():
            while True:
                if not self.tg_token:
                    time.sleep(10)
                    continue
                
                url = f"https://api.telegram.org/bot{self.tg_token}/getUpdates"
                params = {"offset": self.last_update_id + 1, "timeout": 20}
                
                try:
                    res = requests.get(url, params=params, timeout=25)
                    if res.status_code == 200:
                        data = res.json()
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            message = update.get("message", {})
                            text = message.get("text", "")
                            chat_id = str(message.get("chat", {}).get("id", ""))
                            
                            if self.tg_chat_id and chat_id == self.tg_chat_id:
                                self.process_telegram_command(text)
                except Exception:
                    pass
                time.sleep(1)

        thread = threading.Thread(target=listen, daemon=True)
        thread.start()

    def get_btc_price(self):
        sources = [
            ("Bybit", "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", 
             lambda r: float(r.json()["result"]["list"][0]["lastPrice"])),
            ("Coinbase", "https://api.coinbase.com/v2/prices/BTC-USD/spot", 
             lambda r: float(r.json()["data"]["amount"])),
            ("Binance.us", "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT", 
             lambda r: float(r.json()["price"])),
            ("Binance", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", 
             lambda r: float(r.json()["price"])),
            ("OKX", "https://api.okx.com/api/v5/market/ticker?instId=BTC-USDT", 
             lambda r: float(r.json()["data"][0]["last"]))
        ]

        headers = {"User-Agent": "Mozilla/5.0"}
        for name, url, parser in sources:
            try:
                res = requests.get(url, headers=headers, timeout=3)
                if res.status_code == 200:
                    price = parser(res)
                    if price > 0:
                        return price
            except Exception:
                continue
        
        self.api_errors += 1
        return None

    def run(self):
        self.start_telegram_listener()
        start_msg = f"🚀 <b>Бот запущен!</b>\nБаланс: ${self.balance:.2f} | Отслеживание 13:45..."
        self.log(start_msg.replace("<b>", "").replace("</b>", ""))
        self.send_telegram(start_msg)

        while True:
            btc_price = self.get_btc_price()
            now = datetime.now()
            interval_id = f"{now.strftime('%H')}:{(now.minute // 15) * 15:02d}"
            minute = now.minute % 15
            second = now.second
            
            if btc_price is None:
                time.sleep(5)
                continue

            # 1. Завершение сделки
            if self.current_interval != interval_id:
                if self.active_trade is not None:
                    entry_price = self.active_trade["entry_price"]
                    direction = self.active_trade["direction"]
                    stake = self.active_trade["stake"]
                    entry_impulse = self.active_trade["impulse"]
                    
                    price_diff = btc_price - entry_price
                    is_win = (direction == "Up" and price_diff > 0) or \
                             (direction == "Down" and price_diff < 0)
                    
                    if is_win:
                        pnl = stake * (0.37 / 1.50)
                        self.wins += 1
                        self.win_impulses.append(abs(entry_impulse))
                        self.cur_win_streak += 1
                        self.cur_loss_streak = 0
                        self.max_win_streak = max(self.max_win_streak, self.cur_win_streak)
                        res_str = f"<b>WIN 🟢 (+${pnl:.2f})</b>"
                    else:
                        pnl = -stake
                        self.losses += 1
                        self.loss_impulses.append(abs(entry_impulse))
                        self.cur_loss_streak += 1
                        self.cur_win_streak = 0
                        self.max_loss_streak = max(self.max_loss_streak, self.cur_loss_streak)
                        res_str = f"<b>LOSS 🔴 (-${stake:.2f})</b>"
                        
                    self.balance += pnl
                    self.total_pnl += pnl
                    
                    self.trade_history.append({
                        "interval": self.current_interval,
                        "direction": direction,
                        "entry": entry_price,
                        "exit": btc_price,
                        "impulse": entry_impulse,
                        "is_win": is_win
                    })
                    
                    if self.balance > self.peak_balance:
                        self.peak_balance = self.balance
                    dd = ((self.peak_balance - self.balance) / self.peak_balance) * 100
                    if dd > self.max_drawdown_pct:
                        self.max_drawdown_pct = dd
                    
                    # Сохранение состояния после закрытия сделки
                    self.save_state()

                    trade_msg = (
                        f"🏁 <b>СДЕЛКА ЗАКРЫТА [{self.current_interval}]</b>\n"
                        f"Результат: {res_str}\n"
                        f"Вход: ${entry_price:,.1f} ➔ Выход: ${btc_price:,.1f} ({price_diff:+.1f}$)"
                    )
                    self.send_telegram(trade_msg)
                    self.active_trade = None
                    self.send_telegram(self.get_analytics_text())

                self.current_interval = interval_id
                self.start_btc_price = btc_price

            impulse = btc_price - self.start_btc_price if self.start_btc_price else 0.0

            # 2. Мониторинг
            if time.time() - self.last_heartbeat >= 60:
                self.last_heartbeat = time.time()
                self.log(f"👀 Мониторинг [{interval_id}] ({minute:02d}:{second:02d}) | BTC: ${btc_price:,.1f} | Импульс: ${impulse:+.1f} / ${self.min_impulse:.0f}")

            # 3. Вход в сделку
            if minute == 13 and second >= 45 and self.active_trade is None:
                if abs(impulse) >= self.min_impulse:
                    direction = "Up" if impulse > 0 else "Down"
                    stake = round(self.balance * 0.10, 2)
                    
                    self.active_trade = {
                        "direction": direction,
                        "entry_price": btc_price,
                        "stake": stake,
                        "impulse": impulse
                    }
                    
                    enter_msg = (
                        f"🔥 <b>ВХОД В СДЕЛКУ (13:45)!</b>\n"
                        f"Направление: <b>BTC {direction}</b>\n"
                        f"Ставка: <b>${stake:.2f}</b> (10%)\n"
                        f"Цена BTC: ${btc_price:,.1f} | Импульс: ${impulse:+.1f}"
                    )
                    self.send_telegram(enter_msg)

            time.sleep(5)

if __name__ == "__main__":
    bot = PolyBotRailway(15.0)
    bot.run()
                    
