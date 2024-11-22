import streamlit as st
import json
import anthropic
from typing import Dict, List

# Загрузка базы знаний
with open('investigation_knowledge.json', 'r', encoding='utf-8') as f:
    KNOWLEDGE_BASE = json.load(f)

def analyze_situation(case_details: Dict) -> Dict:
    """
    Анализ ситуации с помощью Claude API и базы знаний
    """
    client = anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    
    # Формируем промпт для Claude
    prompt = f"""
    На основе следующих обстоятельств ДТП определи тип ситуации и предложи план расследования:
    
    Обстоятельства дела:
    {json.dumps(case_details, ensure_ascii=False, indent=2)}
    
    База знаний:
    {json.dumps(KNOWLEDGE_BASE, ensure_ascii=False, indent=2)}
    
    Пожалуйста, верни ответ в формате JSON со следующей структурой:
    {{
        "situation_type": "Определенный тип ситуации",
        "primary_actions": ["список первоочередных действий"],
        "required_examinations": ["список необходимых экспертиз"],
        "witness_questions": ["список вопросов для допроса"],
        "special_recommendations": ["особые рекомендации по расследованию"]
    }}
    """
    
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2000,
        temperature=0,
        system="Ты - эксперт по расследованию ДТП. Твоя задача - помогать следователям планировать расследование.",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.content[0].text)

def main():
    st.title("🚗 Помощник следователя по ДТП")
    
    # Боковая панель с информацией
    with st.sidebar:
        st.header("О системе")
        st.info(
            "Система помогает планировать расследование ДТП на основе "
            "введенных обстоятельств дела и базы знаний по тактике расследования."
        )
    
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
    if vehicle_present:
        with st.expander("Сведения о транспортном средстве"):
            vehicle_type = st.text_input("Марка и модель ТС")
            vehicle_damage = st.text_area("Видимые повреждения")
    
    if victim_present:
        with st.expander("Сведения о потерпевшем"):
            victim_condition = st.selectbox(
                "Состояние потерпевшего",
                ["травмирован", "погиб", "легкие повреждения"]
            )
    
    if driver_present:
        with st.expander("Сведения о водителе"):
            driver_condition = st.selectbox(
                "Состояние водителя",
                ["нормальное", "признаки опьянения", "травмирован"]
            )
    
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
                    "details": {
                        "type": vehicle_type,
                        "damage": vehicle_damage
                    } if vehicle_present else None
                },
                "victim": {
                    "present": victim_present,
                    "condition": victim_condition if victim_present else None
                },
                "driver": {
                    "present": driver_present,
                    "condition": driver_condition if driver_present else None
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
                analysis = analyze_situation(case_details)
                
                # Выводим результаты
                st.header("3. План расследования")
                
                st.subheader("Тип ситуации")
                st.info(analysis["situation_type"])
                
                st.subheader("Первоочередные действия")
                for action in analysis["primary_actions"]:
                    st.checkbox(action, key=f"action_{action}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Необходимые экспертизы")
                    for exam in analysis["required_examinations"]:
                        st.markdown(f"- {exam}")
                
                with col2:
                    st.subheader("Вопросы для допроса")
                    for question in analysis["witness_questions"]:
                        st.markdown(f"- {question}")
                
                if analysis.get("special_recommendations"):
                    st.subheader("Особые рекомендации")
                    for rec in analysis["special_recommendations"]:
                        st.markdown(f"- {rec}")
                
            except Exception as e:
                st.error(f"Произошла ошибка при анализе: {str(e)}")

if __name__ == "__main__":
    main()
