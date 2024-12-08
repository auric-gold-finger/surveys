import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json

class MondayAPI:
    def __init__(self):
        self.headers = {
            "Authorization": st.secrets["monday"]["api_token"],
            "Content-Type": "application/json",
        }
        self.api_url = "https://api.monday.com/v2"
        
    def create_item(self, patient_info, survey_results):
        """Create an item in Monday.com board"""
        try:
            query = """
            mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
                create_item (
                    board_id: $boardId,
                    item_name: $itemName,
                    column_values: $columnValues
                ) {
                    id
                }
            }
            """
            
            column_values = {
                # Patient Info
                "name": patient_info["Name"],
                "date__1": datetime.now().strftime("%Y-%m-%d"),
                "age__1": float(patient_info["Age"]),
                "gender__1": patient_info["Gender"],
                "bmi__1": float(patient_info["BMI"]),
                
                # STOP-BANG Results
                "stopbang_score__1": survey_results["STOP-BANG"]["Score"],
                "stopbang_risk__1": survey_results["STOP-BANG"]["Risk Level"],
                "stopbang_details9__1": json.dumps(survey_results["STOP-BANG"]["responses"]),
                
                # Epworth Results
                "ess_score__1": survey_results["Epworth"]["Total Score"],
                "ess_level__1": survey_results["Epworth"]["Interpretation"],
                "ess_details4__1": json.dumps(survey_results["Epworth"]["responses"]),
                
                # PSQI Results
                "psqi_score__1": survey_results["PSQI"]["Global Score"],
                "psqi_details8__1": json.dumps(survey_results["PSQI"]["responses"]),
                
                # MEQ Results
                "meq_score__1": survey_results["MEQ"]["Score"],
                "meq_type__1": survey_results["MEQ"]["Chronotype"],
                "meq_details1__1": json.dumps(survey_results["MEQ"]["responses"])
            }

            variables = {
                "boardId": str(st.secrets["monday"]["board_id"]),  # Convert to string
                "itemName": f"Sleep Survey - {patient_info['Name']}",
                "columnValues": json.dumps(column_values)
            }

            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"query": query, "variables": variables}
            )

            #st.write("Response Status:", response.status_code)
            #st.write("Response:", response.json())

            if response.status_code != 200:
                raise Exception("API error:") # {response.text}")

            response_json = response.json()
            if "errors" in response_json:
                raise Exception("API error") #: {response_json['errors']}")
                
            if "data" not in response_json or "create_item" not in response_json["data"]:
                #st.write("Full API Response:", response_json)  # Debug output
                raise Exception("Unexpected response structure")

            return response_json["data"]["create_item"]["id"]

        except Exception as e:
            st.error(f"Error creating Monday.com item: {str(e)}")
            return None

def store_question_response(responses_dict, survey_type, question_id, question_text, response, score=None):
    """Helper function to store question responses"""
    if survey_type not in responses_dict:
        responses_dict[survey_type] = {}
        
    responses_dict[survey_type][question_id] = {
        'question': question_text,
        'response': response,
        'score': score
    }
    return responses_dict

def main():
    st.title("Sleep Questionnaires")
    
    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 'patient_info'
    if 'patient_info' not in st.session_state:
        st.session_state.patient_info = {}
    if 'results' not in st.session_state:
        st.session_state.results = {}
    if 'responses' not in st.session_state:
        st.session_state.responses = {}

    # Display current step (progress indicator)
    step_map = {
        'patient_info': 'Patient Info',
        'stop_bang': 'STOP-BANG',
        'epworth': 'Epworth',
        'psqi': 'PSQI',
        'meq': 'MEQ',
        'results': 'Results'
    }
    steps = list(step_map.values())
    current_step = steps.index(step_map[st.session_state.step])
    st.progress(current_step / (len(steps) - 1))

    # Patient Information
    if st.session_state.step == 'patient_info':
        st.header("Patient Information")
        with st.form("patient_info_form"):
            name = st.text_input("Name")
            age = st.number_input("Age", min_value=25, max_value=120, value=40)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])  # Exact matches
            height = st.number_input("Height (cm)", min_value=0)
            weight = st.number_input("Weight (kg)", min_value=0)
            
            if st.form_submit_button("Begin Surveys"):
                if name and age and gender and height and weight:
                    st.session_state.patient_info = {
                        "Name": name,
                        "Age": age,
                        "Gender": gender,
                        "Height": height,
                        "Weight": weight,
                        "BMI": round(weight / ((height/100) ** 2), 1) if height and weight else "Not calculated"
                    }
                    st.session_state.step = 'stop_bang'
                    st.rerun()
                else:
                    st.error("Please fill out all fields")

    # STOP-BANG Questionnaire
    elif st.session_state.step == 'stop_bang':
        st.header("STOP-BANG Questionnaire")
        with st.form("stop_bang_form"):
            st.write("Please answer all questions:")
            
            snoring = st.checkbox("Do you Snore loudly (louder than talking or heard through closed doors)?")
            tired = st.checkbox("Do you often feel Tired, fatigued, or sleepy during the day?")
            observed = st.checkbox("Has anyone Observed you stop breathing during sleep?")
            pressure = st.checkbox("Do you have or are being treated for high blood Pressure?")
            bmi = st.checkbox("BMI more than 35 kg/m²?")
            age = st.checkbox("Age over 50 years old?")
            neck = st.checkbox("Neck circumference > 16 inches (40cm)?")
            gender = st.checkbox("Gender = Male?")
            
            if st.form_submit_button("Next"):
                score = sum([snoring, tired, observed, pressure, bmi, age, neck, gender])
                risk = "High Risk" if score >= 5 else "Medium Risk" if score >= 3 else "Low Risk"  # Exact matches
                
                st.session_state.results['STOP-BANG'] = {
                    'Score': score,
                    'Risk Level': risk,
                    'responses': {
                        'Snoring': 'Yes' if snoring else 'No',
                        'Tired': 'Yes' if tired else 'No',
                        'Observed': 'Yes' if observed else 'No',
                        'Pressure': 'Yes' if pressure else 'No',
                        'BMI': 'Yes' if bmi else 'No',
                        'Age': 'Yes' if age else 'No',
                        'Neck': 'Yes' if neck else 'No',
                        'Gender': 'Yes' if gender else 'No'
                    }
                }
                st.session_state.step = 'epworth'
                st.rerun()

    # Epworth Sleepiness Scale
    elif st.session_state.step == 'epworth':
        st.header("Epworth Sleepiness Scale")
        with st.form("epworth_form"):
            st.write("How likely are you to doze off or fall asleep in the following situations?")
            
            situations = [
                "Sitting and reading",
                "Watching TV",
                "Sitting inactive in a public place",
                "As a passenger in a car for 1 hour without break",
                "Lying down to rest in the afternoon",
                "Sitting and talking to someone",
                "Sitting quietly after lunch without alcohol",
                "In a car, while stopped for a few minutes in traffic"
            ]
            
            scores = {}
            for situation in situations:
                score = st.select_slider(
                    situation,
                    options=[0, 1, 2, 3],
                    format_func=lambda x: {
                        0: "Would never doze",
                        1: "Slight chance",
                        2: "Moderate chance",
                        3: "High chance"
                    }[x]
                )
                scores[situation] = score
            
            if st.form_submit_button("Next"):
                total_score = sum(scores.values())
                interpretation = (
                    "Normal" if total_score <= 10
                    else "Borderline" if total_score <= 12
                    else "Mild" if total_score <= 15
                    else "Moderate" if total_score <= 17
                    else "Severe"
                )  # Exact matches
                
                st.session_state.results['Epworth'] = {
                    'Total Score': total_score,
                    'Interpretation': interpretation,
                    'responses': scores
                }
                st.session_state.step = 'psqi'
                st.rerun()

    # PSQI (Simplified for demonstration)
    elif st.session_state.step == 'psqi':
        st.header("Pittsburgh Sleep Quality Index (PSQI)")
        with st.form("psqi_form"):
            st.write("Please answer these questions about your sleep quality:")
            
            sleep_quality = st.select_slider(
                "During the past month, how would you rate your sleep quality overall?",
                options=[0, 1, 2, 3],
                format_func=lambda x: {
                    0: "Very good",
                    1: "Fairly good",
                    2: "Fairly bad",
                    3: "Very bad"
                }[x]
            )
            
            sleep_latency = st.number_input("How long (in minutes) does it usually take you to fall asleep?", 
                                          min_value=0, max_value=180, value=15)
            
            sleep_duration = st.number_input("How many hours of actual sleep do you get at night?", 
                                           min_value=0.0, max_value=12.0, value=7.0, step=0.5)
            
            if st.form_submit_button("Next"):
                global_score = sleep_quality + \
                             (0 if sleep_latency <= 15 else 1 if sleep_latency <= 30 else 2 if sleep_latency <= 60 else 3) + \
                             (0 if sleep_duration > 7 else 1 if sleep_duration > 6 else 2 if sleep_duration > 5 else 3)
                
                st.session_state.results['PSQI'] = {
                    'Global Score': global_score,
                    'responses': {
                        'Sleep Quality': sleep_quality,
                        'Sleep Latency': sleep_latency,
                        'Sleep Duration': sleep_duration
                    }
                }
                st.session_state.step = 'meq'
                st.rerun()

    # MEQ (Simplified for demonstration)
    elif st.session_state.step == 'meq':
        st.header("Morningness-Eveningness Questionnaire")
        with st.form("meq_form"):
            st.write("Please answer these questions about your daily preferences:")
            
            waketime_options = {
                5: "5:00 – 6:30 AM",
                4: "6:30 – 7:45 AM",  # Default normal wake time
                3: "7:45 – 9:45 AM",
                2: "9:45 – 11:00 AM",
                1: "11:00 AM – 12 NOON",
                0: "After 12 NOON"
            }
            
            #st.write("Time options for wake up:")
            #for value, label in waketime_options.items():
            #    st.write(f"{value}: {label}")
                
            preferred_waketime = st.select_slider(
                "What time would you get up if you were entirely free to plan your day?",
                options=list(waketime_options.keys()),
                value=4,  # Default to 6:30-7:45 AM
                format_func=lambda x: waketime_options[x]
            )
            
            bedtime_options = {
                5: "8:00 – 9:00 PM",
                4: "9:00 – 10:15 PM",  # Default normal bedtime
                3: "10:15 PM – 12:30 AM",
                2: "12:30 – 1:45 AM",
                1: "1:45 – 3:00 AM",
                0: "After 3:00 AM"
            }
            
            #st.write("Time options for bedtime:")
            #for value, label in bedtime_options.items():
            #    st.write(f"{value}: {label}")
                
            preferred_bedtime = st.select_slider(
                "What time would you go to bed if you were entirely free to plan your evening?",
                options=list(bedtime_options.keys()),
                value=4,  # Default to 9:00-10:15 PM
                format_func=lambda x: bedtime_options[x]
            )
            
            if st.form_submit_button("See Results"):
                score = (preferred_waketime + preferred_bedtime) * 10
                chronotype = (
                    "Definitely Morning" if score >= 70
                    else "Moderately Morning" if score >= 59
                    else "Neither Type" if score >= 42
                    else "Moderately Evening" if score >= 31
                    else "Definitely Evening"
                )
                
                st.session_state.results['MEQ'] = {
                    'Score': score,
                    'Chronotype': chronotype,
                    'responses': {
                        'Preferred Wake Time': preferred_waketime,
                        'Preferred Bedtime': preferred_bedtime
                    }
                }
                st.session_state.step = 'results'
                st.rerun()

    # Results
    elif st.session_state.step == 'results':
        st.header("Survey Results")
        
        # Handle Monday.com submission only once
        if 'submitted_to_monday' not in st.session_state:
            monday = MondayAPI()
            if monday.create_item(st.session_state.patient_info, st.session_state.results):
                st.success("Results have been saved successfully")
                st.session_state.submitted_to_monday = True
        
        # Display results summary
        #st.subheader("Patient Information")
        #for key, value in st.session_state.patient_info.items():
        #   st.write(f"**{key}:** {value}")
            
        #for survey, data in st.session_state.results.items():
        #    st.subheader(survey)
        #    for key, value in data.items():
        #        if key != 'responses':
        #            st.write(f"**{key}:** {value}")
        
        if st.button("Start New Assessment"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()