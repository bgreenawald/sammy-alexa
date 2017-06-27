import sys
import timeit
import requests
from bs4 import BeautifulSoup

# Dictionary that converts department name acronyms to full department names that the website expects
departments = {
    "cs": "CompSci",
    "stat": "Statistics",
    "anth": "Anthropology"
}

# Dictionarity to map component types to the right form
lect = "lecture"
lab = "laboratory"
disc = "discussion"
component_types = {
    "lectures": lect,
    "lecture": lect,
    "laboratory": lab,
    "laboratories": lab,
    "labs": lab,
    "lab": lab,
    "discussion": disc,
    "discussions": disc
}

start_time = timeit.default_timer()

def lambda_handler(event, context):

    if (event["session"]["application"]["applicationId"] !=
            "amzn1.ask.skill.c3c31cb9-1291-4aea-9d99-1d9d8114086c"):
        raise ValueError("Invalid Application ID")

    if event["session"]["new"]:
        on_session_started({"requestId": event["request"]["requestId"]}, event["session"])

    if event["request"]["type"] == "LaunchRequest":
        return on_launch(event["request"], event["session"])
    elif event["request"]["type"] == "IntentRequest":
        return on_intent(event["request"], event["session"])
    elif event["request"]["type"] == "SessionEndedRequest":
        return on_session_ended(event["request"], event["session"])

def on_session_started(session_started_request, session):
    print "Starting new session."
    print("On start: " + str(timeit.default_timer()- start_time))

def on_launch(launch_request, session):
    return get_welcome_response()

def on_intent(intent_request, session):

    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    print("On intent: " + str(timeit.default_timer()- start_time))
    if intent_name == "GetCourseTime":
        return get_course_time(intent)
    elif intent_name == "GetCourseInstructor":
        return get_course_instructor(intent)
    elif intent_name == "GetCourseAvailability":
        return get_course_availability(intent)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")

def on_session_ended(session_ended_request, session):
    print "Ending session."
    # Cleanup goes here...

def handle_session_end_request():
    card_title = "SAMMY - Thanks"
    speech_output = "Thank you for using the SAMMY skill.  See you next time!"
    should_end_session = True

    return build_response({}, build_speechlet_response(card_title, speech_output, None, should_end_session))

def get_welcome_response():
    session_attributes = {}
    card_title = "SAMMY"
    speech_output = "Welcome to the Alexa Sammy Scheduling Helper. " \
                    "You can ask me for information about courses " \
                    "like course time, instructor, and availability."
    reprompt_text = "Please ask me for a description of a CS course, " \
                    "for example 4740."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_course_time(intent):

    # Extract the JSON information
    course_num = int(intent["slots"]["CourseNumTime"]["value"])
    dept_name = str(intent["slots"]["DeptIDTime"]["value"])
    comp_type = None 
    has_comp = True
    try:
        intent["slots"]["CompTime"]["value"]
    except KeyError:
        has_comp = False

    if has_comp:
        comp_type = str(intent["slots"]["CompTime"]["value"])

    print("Post Info Extract: " + str(timeit.default_timer()- start_time))

    if comp_type != None:
        class_list = web_scrape(dept_name, course_num, comp_type)
    else:
        class_list = web_scrape(dept_name, course_num)

    session_attributes = {}
    
    if(len(class_list)==0):
        card_title = "SAMMY Course Description"
        speech_output = "I can't seem to find the class you're looking for. " \
                        "Please try again."
        reprompt_text = "I'm not sure which class number you are asking for. " \
                        "Try asking about 4740 or 2150 for example."
    else:
        card_title = "SAMMY Course Time for CS" + str(course_num)
        if comp_type == None:
            speech_output = dept_name + str(course_num) + " meets on "
        else:
            speech_output = "The " + str(comp_type) + " for " + dept_name + str(course_num) + " meets on "

        for _class in class_list:
            speech_output += time_parser(_class.time) + " and "
        speech_output = speech_output[0:len(speech_output) - 4]
        reprompt_text = ""

    should_end_session = False

    print("Post info prep: " + str(timeit.default_timer()- start_time))

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))  

def get_course_instructor(intent):

    # Extract the JSON information
    course_num = int(intent["slots"]["CourseNumInst"]["value"])
    dept_name = str(intent["slots"]["DeptIDInst"]["value"])
    comp_type = None 
    has_comp = True

    try:
        intent["slots"]["CompInst"]["value"]
    except KeyError:
        has_comp = False

    if has_comp:
        comp_type = str(intent["slots"]["CompInst"]["value"])

    if comp_type != None:
        class_list = web_scrape(dept_name, course_num, comp_type)
    else:
        class_list = web_scrape(dept_name, course_num)

    # Get the set of unique instructors
    unique_instructors = []
    unique_instructors = set([x.instructor for x in class_list])
    
    session_attributes = {}
    
    if(len(class_list)==0):
        card_title = "SAMMY Course Description"
        speech_output = "I can't seem to find the class you're looking for. " \
                        "Please try again."
        reprompt_text = "I'm not sure which class number you are asking for. " \
                        "Try asking about CS 4740 or CS 2150 for example."
    else:
        card_title = "SAMMY Course Instructor for CS" + str(course_num)
        if comp_type == None:
            speech_output = dept_name  + str(course_num) + " is taught by "
        else:
            speech_output = "The " + str(comp_type) + " for " + dept_name + str(course_num) + " is taught by "
            
        for inst in unique_instructors:
            speech_output += inst + " and "

        speech_output = speech_output[0:len(speech_output) - 4]
        reprompt_text = ""

    should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))  
    
def get_course_availability(intent):

    # Extract the JSON information
    course_num = int(intent["slots"]["CourseNumAv"]["value"])
    dept_name = str(intent["slots"]["DeptIDAv"]["value"])
    comp_type = None 
    has_comp = True

    try:
        intent["slots"]["CompAv"]["value"]
    except KeyError:
        has_comp = False

    if has_comp:
        comp_type = str(intent["slots"]["CompAv"]["value"]).lower()

    if comp_type != None:
        class_list = web_scrape(dept_name, course_num, comp_type)
    else:
        class_list = web_scrape(dept_name, course_num)

    session_attributes = {}

    # Get the number of open sections
    num_open = len([x.is_full for x in class_list if x.is_full])
    
    if(len(class_list)==0):
        card_title = "SAMMY Course Description"
        speech_output = "I can't seem to find the class you're looking for. " \
                        "Please try again."
        reprompt_text = "I'm not sure which class number you are asking for. " \
                        "Try asking about CS 4740 or CS 2150 for example."
    else:
        card_title = "SAMMY Course Instructor for CS" + str(course_num)
        if comp_type == None:
            speech_output = dept_name + str(course_num) + " has "
        else:
            speech_output = "The " + str(comp_type) + " for " + dept_name + str(course_num) + " has "
            
        speech_output += str(num_open) + " open sections "

        reprompt_text = ""

    should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))  
        
def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }

def time_parser(old_time):
    return old_time.replace("-", "to").replace("mo", "Monday, ").replace("tu", "Tuesday, ").replace("we", "wednesday, ").replace("th", "Thursday, ").replace("fr", "Friday, ")

def web_scrape(department_name, course_num, comp_type = None):
    
    # Read in all classes in the given department and parse the page with the BeautifulSoup library
    base_url = "https://rabi.phys.virginia.edu/mySIS/CS2/page.php?Semester=1178&Type=Group&Group=" + departments[department_name]
    page = requests.get(base_url)
    soup = BeautifulSoup(page.content, 'html.parser')

    print("Post web read: " + str(timeit.default_timer()- start_time))
    # Get the page data for the course number of interest
    full_class_name = department_name.upper() + str(course_num)
    result_set = list(soup.find_all("tr", class_="SectionOdd S {0}".format(full_class_name)))
    result_set += list(soup.find_all("tr", class_="SectionEven S {0}".format(full_class_name)))

    print("Post web search: " + str(timeit.default_timer()- start_time))
    
    return_list = []

    # For each component found, extract relevamt information from component
    for component in result_set:
        res_list = list(component.find_all("td"))
        component_type = res_list[2].text.split(" ")[0].lower()
        is_full = "Open" in str(res_list[3].text)
        instructor = res_list[len(res_list)-3].text.lower()
        time = res_list[len(res_list)-2].text.lower()
        location = res_list[len(res_list)-1].text.lower()
        return_list.append(ClassComponent(component_type, instructor, location, time, is_full))

    print("Post info: " + str(timeit.default_timer()- start_time))

    if comp_type != None:
        return [x for x in return_list if x.component == component_types[comp_type.lower()]]
    else:
        return return_list

class ClassComponent(object):

    """A class that represents a single component of a given class (lecture, lab, ect)"""
    def __init__(self, component, instructor, location, time, is_full):
        super(ClassComponent, self).__init__()
        self.component = component
        self.instructor = instructor
        self.time = time
        self.location = location
        self.is_full = is_full