import streamlit as st
import pandas as pd
# --- БЛОК АВТОРИЗАЦИИ ---
def check_password():
    """Проверяет правильность введенного пароля."""
    
    # Функция, которая срабатывает при вводе текста
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Удаляем пароль из памяти для безопасности
        else:
            st.session_state["password_correct"] = False

    # Если статус пароля еще не определен (первый заход)
    if "password_correct" not in st.session_state:
        st.text_input(
            "🔒 Введите пароль для доступа к калькулятору", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    
    # Если ввели неверно
    elif not st.session_state["password_correct"]:
        st.text_input(
            "🔒 Введите пароль для доступа к калькулятору", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Неверный пароль. Попробуйте еще раз.")
        return False
    
    # Если пароль верный - пропускаем дальше
    return True

# Если пароль не введен или неверен - останавливаем отрисовку остального приложения
if not check_password():
    st.stop()
# Кэшируем запрос к ЦБ, чтобы не дергать сайт при каждом нажатии кнопок
@st.cache_data(ttl=3600)
def fetch_cbr_rates():
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    try:
        df = pd.read_xml(url, encoding='cp1251')
        df['Value'] = df['Value'].astype(str).str.replace(',', '.').astype(float)
        df['Nominal'] = df['Nominal'].astype(float)
        df['Rate'] = df['Value'] / df['Nominal']
        rates_dict = df.set_index('CharCode')['Rate'].to_dict()
        return {
            'CNY': rates_dict.get('CNY', 0.0),
            'KRW': rates_dict.get('KRW', 0.0),
            'USD': rates_dict.get('USD', 0.0),
            'EUR': rates_dict.get('EUR', 0.0)
        }
    except Exception as e:
        return None

# --- БЛОК РАСЧЕТОВ (ваша логика) ---
def get_customs_fee(price_rub):
    if price_rub <= 200000: return 775
    elif price_rub <= 450000: return 1550
    elif price_rub <= 1200000: return 3100
    elif price_rub <= 2700000: return 8530
    elif price_rub <= 4200000: return 12000
    elif price_rub <= 5500000: return 15500
    elif price_rub <= 7000000: return 20000
    elif price_rub <= 8000000: return 23000
    elif price_rub <= 9000000: return 25000
    elif price_rub <= 10000000: return 27000
    else: return 30000

def calc_duty(age_idx, price_eur, vol):
    if age_idx == 0: # До 3 лет
        if price_eur <= 8500: return max(price_eur * 0.54, vol * 2.5)
        elif price_eur <= 16700: return max(price_eur * 0.48, vol * 3.5)
        elif price_eur <= 42300: return max(price_eur * 0.48, vol * 5.5)
        elif price_eur <= 84500: return max(price_eur * 0.48, vol * 7.5)
        elif price_eur <= 169000: return max(price_eur * 0.48, vol * 15.0)
        else: return max(price_eur * 0.48, vol * 20.0)
    elif age_idx == 1: # 3-5 лет
        if vol <= 1000: return vol * 1.5
        elif vol <= 1500: return vol * 1.7
        elif vol <= 1800: return vol * 2.5
        elif vol <= 2300: return vol * 2.7
        elif vol <= 3000: return vol * 3.0
        else: return vol * 5.7
    else: # Старше 5 лет
        if vol <= 1000: return vol * 3.0
        elif vol <= 1500: return vol * 3.2
        elif vol <= 1800: return vol * 3.5
        elif vol <= 2300: return vol * 4.8
        elif vol <= 3000: return vol * 5.0
        else: return vol * 5.7

def get_util_fee(age_idx, vol, hp):
    is_new = (age_idx == 0)
    if hp > 160 or vol > 3000:
        if vol <= 1000: return 150000 if is_new else 250000
        elif vol <= 2000: return 556000 if is_new else 944000
        elif vol <= 3000: return 1564000 if is_new else 2210000
        elif vol <= 3500: return 1970000 if is_new else 2830000
        else: return 2284000 if is_new else 3260000
    else:
        return 3400 if is_new else 5200

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Калькулятор Импорта Авто", layout="centered")
st.title("🚗 Калькулятор импорта авто в РФ")

rates = fetch_cbr_rates()
if not rates or rates['EUR'] == 0:
    st.error("Ошибка синхронизации с ЦБ РФ. Проверьте интернет.")
    st.stop()

# Плашка с курсами валют
st.info(f"**Актуальные курсы ЦБ РФ:** 1 ¥ = {rates['CNY']:.2f} ₽ | 1000 ₩ = {rates['KRW']*1000:.2f} ₽ | 1 € = {rates['EUR']:.2f} ₽")

# Создаем две колонки для интерфейса
col1, col2 = st.columns(2)

with col1:
    currency = st.selectbox("Валюта покупки", ["CNY (Юань)", "KRW (Вона)", "USD", "EUR"])
    car_price = st.number_input("Стоимость авто", min_value=0.0, value=150000.0, step=1000.0)
    age_str = st.selectbox("Возраст авто", ["До 3 лет", "От 3 до 5 лет", "Старше 5 лет"])

with col2:
    engine_volume = st.number_input("Объем двигателя (см³)", min_value=0, value=1998, step=100)
    horsepower = st.number_input("Мощность (л.с.)", min_value=0, value=150, step=10)
    delivery = st.number_input("Доставка в РФ (₽)", min_value=0, value=300000, step=10000)
    docs = st.number_input("Брокер, СБКТС, ЭПТС (₽)", min_value=0, value=70000, step=5000)

# Маппинг данных
cur_key = currency.split(" ")[0]
age_idx = ["До 3 лет", "От 3 до 5 лет", "Старше 5 лет"].index(age_str)
is_commercial = (horsepower > 160 or engine_volume > 3000)

# Кнопка расчета
if st.button("Рассчитать стоимость под ключ", type="primary", use_container_width=True):
    # Математика
    price_rub = car_price * rates[cur_key]
    price_eur = price_rub / rates['EUR']
    
    duty_eur = calc_duty(age_idx, price_eur, engine_volume)
    duty_rub = duty_eur * rates['EUR']
    
    util_fee = get_util_fee(age_idx, engine_volume, horsepower)
    customs_fee = get_customs_fee(price_rub)
    
    total = price_rub + duty_rub + util_fee + customs_fee + delivery + docs
    
    # Вывод результатов
    st.divider()
    if is_commercial:
        st.warning("⚠️ Внимание: Мощность > 160 л.с. или объем > 3.0л. Включен **коммерческий** утильсбор!")
    else:
        st.success("✅ Применен **льготный** утильсбор (для личного пользования).")

    st.subheader(f"Итоговая цена: {total:,.0f} ₽".replace(",", " "))
    
    # Таблица детализации
    details = {
        "Статья расходов": ["Цена авто за рубежом", "Таможенная пошлина", "Утилизационный сбор", "Сбор таможни за оформление", "Логистика", "Документы (СБКТС/ЭПТС)"],
        "Сумма (₽)": [f"{price_rub:,.0f}", f"{duty_rub:,.0f}", f"{util_fee:,.0f}", f"{customs_fee:,.0f}", f"{delivery:,.0f}", f"{docs:,.0f}"]
    }
    st.table(pd.DataFrame(details))