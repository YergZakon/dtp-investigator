import streamlit as st
import json
from anthropic import Anthropic
from typing import Dict, List
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Загрузка базы знаний
with open('investigation_knowledge.json', 'r', encoding='utf-8') as f:
    KNOWLEDGE_BASE = json.load(f)

def get_api_key() -> str:
    """
    Получение API ключа из разных источников
    """
    # Проверяем наличие API ключа в разных местах
    api_key = (
        os.getenv('ANTHROPIC_API_KEY') or  # Из переменных окружения
        st.secrets.get("ANTHROPIC_API_KEY", None) or  # Из secrets Streamlit
        st.session_state.get('ANTHROPIC_API_KEY', None)  # Из session state
    )
    
    if not api_key:
        # Если ключ не найден, запрашиваем его у пользователя
        if 'ANTHROPIC_API_KEY' not in st.session_state:
            st.session_state.ANTHROPIC_API_KEY = st.text_input(
                "Введите ваш Anthropic API ключ:",
                type="password"
            )
        api_key = st.session_state.ANTHROPIC_API_KEY
    
    return api_key

def analyze_situation(case_details: Dict) -> Dict:
    """
    Анализ ситуации с помощью Claude API и базы знаний
    """
    api_key = get_api_key()
    
    if not api_key:
        st.error("API ключ не найден. Пожалуйста, введите API ключ.")
        st.stop()
    
    client = Anthropic(api_key=api_key)
    
    prompt = f"""
    На основе следующих обстоятельств ДТП определи тип ситуации и предложи план расследования.
    
    Обстоятельства дела:
    {json.dumps(case_details, ensure_ascii=False, indent=2)}
    
    База знаний:
    {json.dumps(KNOWLEDGE_BASE, ensure_ascii=False, indent=2)}
    
    На основе анализа этих данных, пожалуйста:
    1. Определи тип следственной ситуации
    2. Составь список первоочередных действий
    3. Предложи необходимые экспертизы
    4. Составь подробный план допросов участников

    Важно: верни ответ строго в следующем формате JSON (все поля обязательны):
    {{
        "situation_type": "описание типа ситуации",
        "primary_actions": [
            "список первоочередных действий"
        ],
        "required_examinations": [
            "список необходимых экспертиз"
        ],
        "interrogation_plan": {{
            "witness_questions": {{
                "general": [
                    "общие вопросы для свидетелей"
                ],
                "specific": [
                    "вопросы с учетом конкретной ситуации"
                ],
                "technical": [
                    "вопросы о технических аспектах"
                ]
            }},
            "driver_questions": {{
                "pre_incident": [
                    "вопросы о событиях до ДТП"
                ],
                "incident": [
                    "вопросы о самом ДТП"
                ],
                "post_incident": [
                    "вопросы о действиях после ДТП"
                ],
                "technical": [
                    "вопросы о техническом состоянии ТС"
                ]
            }},
            "victim_questions": {{
                "pre_incident": [
                    "вопросы о событиях до ДТП"
                ],
                "incident": [
                    "вопросы о самом ДТП"
                ],
                "health": [
                    "вопросы о состоянии здоровья"
                ]
            }}
        }},
        "special_recommendations": [
            "особые рекомендации по расследованию"
        ]
    }}

    Обязательно включи все секции вопросов, учитывая:
    - Тип ДТП ({case_details['incident_type']})
    - Наличие/отсутствие участников (водитель: {case_details['participants']['driver']['present']}, 
      потерпевший: {case_details['participants']['victim']['present']})
    - Условия происшествия (погода: {case_details['conditions']['weather']}, 
      освещение: {case_details['conditions']['lighting']})
    """
    
    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            temperature=0,
            system="Ты - опытный следователь-криминалист, специализирующийся на расследовании ДТП. Твоя задача - помочь составить подробный план расследования и список вопросов для допроса всех участников. Строго придерживайся указанного формата JSON в ответе.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            response_text = response.content[0].text
            
            # Пытаемся найти JSON в ответе, если он окружен другим текстом
            try:
                # Сначала пробуем распарсить весь ответ
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Если не получилось, ищем структуру, похожую на JSON
                import re
                json_match = re.search(r'({[\s\S]*})', response_text)
                if json_match:
                    return json.loads(json_match.group(1))
                else:
                    raise ValueError("Не удалось найти JSON в ответе")
                    
        except json.JSONDecodeError as e:
            st.error("Ошибка при парсинге ответа API")
            st.error("Ответ API:")
            st.code(response_text, language="json")
            raise ValueError(f"Некорректный формат JSON в ответе API: {str(e)}")
        except Exception as e:
            st.error("Непредвиденная ошибка при обработке ответа API")
            st.error(f"Тип ошибки: {type(e).__name__}")
            st.error(f"Описание ошибки: {str(e)}")
            st.error("Ответ API:")
            st.code(response_text, language="text")
            raise e
            
    except Exception as e:
        st.error("Ошибка при запросе к API")
        st.error(f"Тип ошибки: {type(e).__name__}")
        st.error(f"Описание ошибки: {str(e)}")
        raise e

    # Если мы дошли до этой точки без возврата данных или исключения,
    # значит что-то пошло не так
    raise ValueError("Не удалось получить корректный ответ от API")

def display_interrogation_plan(analysis: Dict):
    """
    Отображение плана допросов с проверкой наличия всех ключей
    """
    st.header("4. План допросов")
    
    interrogation_plan = analysis.get("interrogation_plan", {})
    
    # Вопросы для свидетелей
    witness_questions = interrogation_plan.get("witness_questions", {})
    with st.expander("📝 Вопросы для свидетелей", expanded=True):
        if witness_questions.get("general"):
            st.subheader("Общие вопросы")
            for q in witness_questions["general"]:
                st.checkbox(q, key=f"w_gen_{hash(q)}")
            
        if witness_questions.get("specific"):
            st.subheader("Специфические вопросы")
            for q in witness_questions["specific"]:
                st.checkbox(q, key=f"w_spec_{hash(q)}")
            
        if witness_questions.get("technical"):
            st.subheader("Технические аспекты")
            for q in witness_questions["technical"]:
                st.checkbox(q, key=f"w_tech_{hash(q)}")

    # Вопросы для водителя
    driver_questions = interrogation_plan.get("driver_questions", {})
    if driver_questions:
        with st.expander("🚗 Вопросы для водителя", expanded=True):
            if driver_questions.get("pre_incident"):
                st.subheader("События до ДТП")
                for q in driver_questions["pre_incident"]:
                    st.checkbox(q, key=f"d_pre_{hash(q)}")
            
            if driver_questions.get("incident"):
                st.subheader("О происшествии")
                for q in driver_questions["incident"]:
                    st.checkbox(q, key=f"d_inc_{hash(q)}")
            
            if driver_questions.get("post_incident"):
                st.subheader("После происшествия")
                for q in driver_questions["post_incident"]:
                    st.checkbox(q, key=f"d_post_{hash(q)}")
            
            if driver_questions.get("technical"):
                st.subheader("Техническое состояние ТС")
                for q in driver_questions["technical"]:
                    st.checkbox(q, key=f"d_tech_{hash(q)}")

    # Вопросы для потерпевшего
    victim_questions = interrogation_plan.get("victim_questions", {})
    if victim_questions:
        with st.expander("🤕 Вопросы для потерпевшего", expanded=True):
            if victim_questions.get("pre_incident"):
                st.subheader("События до ДТП")
                for q in victim_questions["pre_incident"]:
                    st.checkbox(q, key=f"v_pre_{hash(q)}")
            
            if victim_questions.get("incident"):
                st.subheader("О происшествии")
                for q in victim_questions["incident"]:
                    st.checkbox(q, key=f"v_inc_{hash(q)}")
            
            if victim_questions.get("health"):
                st.subheader("Состояние здоровья")
                for q in victim_questions["health"]:
                    st.checkbox(q, key=f"v_health_{hash(q)}")
def main():
    st.title("🚗 Помощник следователя по ДТП")
    
    # Боковая панель с информацией
    with st.sidebar:
        st.header("О системе")
        st.info(
            "Система помогает планировать расследование ДТП на основе "
            "введенных обстоятельств дела и базы знаний по тактике расследования."
        )
        
        # Добавляем возможность изменить API ключ в сайдбаре
        if st.button("Изменить API ключ"):
            st.session_state.ANTHROPIC_API_KEY = None
    
    # Проверяем наличие API ключа перед отображением основного интерфейса
    api_key = get_api_key()
    if not api_key:
        st.warning("Пожалуйста, введите API ключ для продолжения работы.")
        return
    
    # Основная форма
    st.header("1. Обстоятельства происшествия")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_time = st.date_input("Дата происшествия")
        location = st.text_input("Место происшествия")
        incident_type = st.selectbox(
            "Тип происшествия",
            [
                "наезд на пешехода",
                "столкновение",
                "опрокидывание",
                "наезд на препятствие",
                "иное"
            ]
        )
    
    with col2:
        vehicle_present = st.checkbox("Транспортное средство на месте")
        victim_present = st.checkbox("Потерпевший на месте")
        driver_present = st.checkbox("Водитель на месте")
    
    st.header("2. Дополнительные сведения")
    
    # Дополнительная информация в зависимости от наличия участников
    vehicle_details = {}
    if vehicle_present:
        with st.expander("Сведения о транспортном средстве"):
            vehicle_type = st.text_input("Марка и модель ТС")
            vehicle_damage = st.text_area("Видимые повреждения")
            vehicle_details = {
                "type": vehicle_type,
                "damage": vehicle_damage
            }
    
    victim_details = {}
    if victim_present:
        with st.expander("Сведения о потерпевшем"):
            victim_condition = st.selectbox(
                "Состояние потерпевшего",
                ["травмирован", "погиб", "легкие повреждения"]
            )
            victim_details = {"condition": victim_condition}
    
    driver_details = {}
    if driver_present:
        with st.expander("Сведения о водителе"):
            driver_condition = st.selectbox(
                "Состояние водителя",
                ["нормальное", "признаки опьянения", "травмирован"]
            )
            driver_details = {"condition": driver_condition}
    
    # Дополнительные обстоятельства
    with st.expander("Условия происшествия"):
        weather = st.selectbox(
            "Погодные условия",
            ["ясно", "пасмурно", "дождь", "снег", "туман"]
        )
        road_condition = st.selectbox(
            "Состояние дороги",
            ["сухое", "мокрое", "гололед", "снежное"]
        )
        lighting = st.selectbox(
            "Освещение",
            ["светлое время", "темное время", "сумерки"]
        )
    
    # Кнопка анализа
    if st.button("Проанализировать ситуацию", type="primary"):
        # Собираем все данные в словарь
        case_details = {
            "date_time": str(date_time),
            "location": location,
            "incident_type": incident_type,
            "participants": {
                "vehicle": {
                    "present": vehicle_present,
                    "details": vehicle_details if vehicle_present else None
                },
                "victim": {
                    "present": victim_present,
                    "details": victim_details if victim_present else None
                },
                "driver": {
                    "present": driver_present,
                    "details": driver_details if driver_present else None
                }
            },
            "conditions": {
                "weather": weather,
                "road": road_condition,
                "lighting": lighting
            }
        }
        
        with st.spinner("Анализирую ситуацию..."):
            try:
                # Сохраняем результат анализа в session state
                st.session_state.analysis_result = analyze_situation(case_details)
                analysis = st.session_state.analysis_result
                
                # Выводим результаты
                st.header("3. План расследования")
                
                st.subheader("Тип ситуации")
                st.info(analysis["situation_type"])
                
                # Первоочередные действия
                with st.expander("🎯 Первоочередные действия", expanded=True):
                    for action in analysis["primary_actions"]:
                        st.checkbox(action, key=f"action_{action}")
                
                # Экспертизы
                with st.expander("🔍 Необходимые экспертизы", expanded=True):
                    for exam in analysis["required_examinations"]:
                        st.markdown(f"- {exam}")
                
                # План допросов
                display_interrogation_plan(analysis)
                
                # Особые рекомендации
                if analysis.get("special_recommendations"):
                    with st.expander("💡 Особые рекомендации", expanded=True):
                        for rec in analysis["special_recommendations"]:
                            st.markdown(f"- {rec}")
                
            except Exception as e:
                st.error(f"Произошла ошибка при анализе: {str(e)}")
                st.exception(e)  # Правильный способ показать подробности ошибки

if __name__ == "__main__":
    main()