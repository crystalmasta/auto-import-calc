import streamlit as st
import pandas as pd
import requests

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

# Кэшируем запрос на 1 час, чтобы не перегружать сеть при каждом клике
@st.cache_data(ttl=3600)
def fetch_cbr_rates():
    # Используем официальное зеркало ЦБ, которое открыто для зарубежных серверов Streamlit
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Извлекаем данные и обязательно делим на 'Nominal' (для воны это 1000, для юаня 1),
        # чтобы получить чистую стоимость 1 единицы валюты, как в вашем первоначальном коде.
        return {
            'CNY': float(data['Valute']['CNY']['Value']) / data['Valute']['CNY']['Nominal'],
            'KRW': float(data['Valute']['KRW']['Value']) / data['Valute']['KRW']['Nominal'],
            'USD': float(data['Valute']['USD']['Value']) / data['Valute']['USD']['Nominal'],
            'EUR': float(data['Valute']['EUR']['Value']) / data['Valute']['EUR']['Nominal']
        }
    except Exception as e:
        return None

# --- БЛОК РАСЧЕТОВ (ваша логика) ---
def get_customs_fee(price_rub):
    # Обновленные проиндексированные ставки таможенного оформления
    if price_rub <= 200000: return 1067
    elif price_rub <= 450000: return 2134
    elif price_rub <= 1200000: return 4269
    elif price_rub <= 2700000: return 13541  
    elif price_rub <= 4200000: return 19210
    elif price_rub <= 5500000: return 24545
    elif price_rub <= 7000000: return 32017
    elif price_rub <= 8000000: return 37353
    elif price_rub <= 9000000: return 42689
    elif price_rub <= 10000000: return 48025
    else: return 53362

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
        # Новая коммерческая сетка утильсбора после индексации
        if vol <= 1000: return 256800 if is_new else 427600
        elif vol <= 2000: return 952800 if is_new else 1618000
        elif vol <= 3000: return 2671200 if is_new else 3772400
        elif vol <= 3500: return 3363200 if is_new else 4831600
        else: return 3899600 if is_new else 5565200
    else:
        # Льготный утиль для физлиц
        return 3400 if is_new else 5200

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="Калькулятор Импорта Авто", layout="centered")
st.title("🚗 Калькулятор импорта авто DealerPro")

# Вызываем функцию получения курсов
rates = fetch_cbr_rates()
if not rates or rates['EUR'] == 0:
    st.error("Ошибка синхронизации с сервером валют. Проверьте интернет.")
    st.stop()

# Плашка с актуальными курсами валют
st.info(f"**Актуальные курсы ЦБ РФ:** 1 ¥ = {rates['CNY']:.2f} ₽ | 1000 ₩ = {rates['KRW']*1000:.2f} ₽ | 1 $ = {rates['USD']:.2f} ₽ | 1 € = {rates['EUR']:.2f} ₽")

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
    markup = st.number_input("Наша комиссия / Наценка (₽)", min_value=0, value=50000, step=5000) # ДОБАВЛЕНО ПОЛЕ КОМИССИИ

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
    
    # Включаем комиссию в итоговую сумму
    total = price_rub + duty_rub + util_fee + customs_fee + delivery + docs + markup
    
    # Вывод результатов
    st.divider()
    if is_commercial:
        st.warning("⚠️ Внимание: Мощность > 160 л.с. или объем > 3.0л. Включен **коммерческий** утильсбор!")
    else:
        st.success("✅ Применен **льготный** утильсбор (для личного пользования).")

    st.subheader(f"Итоговая цена: {total:,.0f} ₽".replace(",", " "))
    
    # Таблица детализации с добавленным пунктом
    details = {
        "Статья расходов": [
            "Цена авто за рубежом", 
            "Таможенная пошлина", 
            "Утилизационный сбор", 
            "Сбор таможни за оформление", 
            "Логистика", 
            "Документы (СБКТС/ЭПТС)",
            "Комиссия компании" # ДОБАВЛЕНО В ТАБЛИЦУ
        ],
        "Сумма (₽)": [
            f"{price_rub:,.0f}", 
            f"{duty_rub:,.0f}", 
            f"{util_fee:,.0f}", 
            f"{customs_fee:,.0f}", 
            f"{delivery:,.0f}", 
            f"{docs:,.0f}",
            f"{markup:,.0f}" # ДОБАВЛЕНО В ТАБЛИЦУ
        ]
    }
    st.table(pd.DataFrame(details))