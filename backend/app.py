from flask import Flask, jsonify, request 
from flask import url_for, redirect
from flask_cors import CORS
import json
from types import SimpleNamespace
import threading
import time
import openai

with open("api_key.txt", "r") as f:
    openai.api_key = f.read().strip()

lock = threading.Lock()

app = Flask(__name__, static_url_path='/static')
CORS(app)

def load_data_from_file(file_name):
    with open(file_name + "-writingtheory.json", "r") as f:
        return json.loads(f.read(), object_hook = lambda d: SimpleNamespace(**d))

def save_data_to_file(file_name, data):
    with open(file_name + "-writingtheory.json", "w") as f:
        f.write(json.dumps(data, default=lambda o: o.__dict__, indent=4))

def save_error_log(error):
    error_data = load_data_from_file("errors")
    error_data.append({"error": error, "time": int(time.time())})
    save_data_to_file("error", error_data)

@app.route('/')
def home():
    return redirect(url_for('static', filename='index.html'))
    
'''
Structure of "ideas.json":
[
    {
        "username": "username",
        "ideas": [
            "idea1",
            "idea2",
            "idea3"
        ]
    }
]
'''

initialMessages = [
    "Feedback develops writing skills for academic and professional success",
    "Feedback tailors assignments to meet professor's expectations for better grades",
    "Feedback improves critical thinking skills and leads to better decision-making"
]

initialMessages_evaluation = [
    "Avoid using informal language such as \"you guys\" in academic or professional writing.",
    "Avoid repetition, as there is here with defensiveness; instead consolidate similar points for greater clarity and conciseness.",
    "Include specific examples or anecdotes to highlight the importance of accepting feedback from professors, making your statement more relatable and impactful."
]


def createGPTMessagesArray(currentIdeas, currentPage, currentText):
    cleanedText = currentText.replace('"', "'")
    messages = []
    if currentPage == "study":
        messages = [{"role": "system", "content": "You provide one example idea per response. Give only the idea without any preamble or comment. Be as brief as possible."}, {"role": "user", "content": "Give me an example idea that convinces a bright but stubborn 20-year old male student that was asked by his professor whether he wants feedback on his latest term paper to agree to receive the feedback."}]
        for idea in currentIdeas:
            messages.append({"role": "assistant", "content": idea})
            messages.append({"role": "user", "content": "Do the same but with a new idea."})
    elif currentPage == "evaluation":
        messages = [{"role": "system", "content": "You evaluate text and give one suggestion for improvement. Give only the suggestion without any preamble or comment. Be as brief as possible."}, {"role": "user", "content": "This is my message: \"" + cleanedText + "\""}]
        for idea in currentIdeas:
            messages.append({"role": "assistant", "content": idea})
            messages.append({"role": "user", "content": "Do the same but with a completely new suggestion."})
    return messages

def getNewIdeaFromGPT(messages):
    print("Getting from GPT:" + str(messages))
    msg = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
    )
    new_idea = msg['choices'][0]['message']['content']
    print("Got from GPT:" + str(new_idea))
    return new_idea

@app.route('/getNewExampleIdea', methods=['POST'])
def get_new_example_idea():
    username = request.json['username']
    text = request.json['text']
    currentPage = request.json['currentPage']
    print("got request from '" + username + "' current page '" + currentPage + "' with text: " + text)
    lock.acquire()
    try:
        ideas_data = load_data_from_file("ideas")
        for user in ideas_data:
            if user.username == username and user.currentPage == currentPage:
                messages = createGPTMessagesArray(user.ideas, currentPage, text)
                new_idea = getNewIdeaFromGPT(messages)
                user.ideas.append(new_idea)
                save_data_to_file("ideas", ideas_data)
                each_idea_data = load_data_from_file("each_idea")
                each_idea_data.append({"username": username, "text": text, "idea": new_idea, "currentPage": currentPage, "time": int(time.time())})
                save_data_to_file("each_idea", each_idea_data)
                lock.release()
                return jsonify({"success": True, "idea": new_idea})
        initials = initialMessages if currentPage == "study" else initialMessages_evaluation
        messages = createGPTMessagesArray(initials, currentPage, text)
        new_idea = getNewIdeaFromGPT(messages)
        ideas_data.append({"username": username, "ideas": initials + [new_idea], "currentPage": currentPage})
        save_data_to_file("ideas", ideas_data)
        each_idea_data = load_data_from_file("each_idea")
        each_idea_data.append({"username": username, "text": text, "idea": new_idea, "currentPage": currentPage, "time": int(time.time())})
        save_data_to_file("each_idea", each_idea_data)
        lock.release()
        return jsonify({"success": True, "idea": new_idea})
    except Exception as e:
        print(e)
        save_error_log("getNewExampleIdea")
        lock.release()
        return jsonify({"success": False, "idea": ""})

@app.route('/submit', methods=['POST'])
def submit():
    text = request.json['text']
    username = request.json['username']
    studyGroup = request.json['studyGroup']
    evaluationGroup = request.json['evaluationGroup']
    currentPage = request.json['currentPage']
    keystrokes = request.json['keystrokes']
    helpTaps = request.json['helpTaps']
    lock.acquire()
    try:
        submissions_data = load_data_from_file("submissions")
        submissions_data.append({"username": username, "text": text, "studyGroup": studyGroup, "evaluationGroup": evaluationGroup, "currentPage": currentPage, "time": int(time.time())})
        save_data_to_file("submissions", submissions_data)
    except Exception as e:
        print(e)
        save_error_log("submit-submissions")
        lock.release()
        return jsonify({"success": False})

    try:
        keystrokes_data = load_data_from_file("keystrokes")
        keystrokes_data.append({"username": username, "keystrokes": keystrokes, "time": int(time.time()), "currentPage": currentPage})
        save_data_to_file("keystrokes", keystrokes_data)
    except Exception as e:
        print(e)
        save_error_log("submit-keystrokes")

    if len(helpTaps) > 0:
        try:
            helpTaps_data = load_data_from_file("helpTaps")
            helpTaps_data.append({"username": username, "helpTaps": helpTaps, "time": int(time.time()), "currentPage": currentPage})
            save_data_to_file("helpTaps", helpTaps_data)
        except Exception as e:
            print(e)
            save_error_log("submit-helpTaps")

    lock.release()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5001, debug = True)
