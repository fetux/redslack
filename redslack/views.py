from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from redmine import Redmine
from models import User

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


redmine = None

@api_view(['POST'])
def router(request):
    """
    API entry point that routes outside world requests
    """
    non_auth_commands = ['connect', 'help']
    data = request._get_post()
    params = data['text'].split()
    command = params[0]
    if command not in non_auth_commands:
        try:
            user = User.objects.get(slack_id=data['user_id'])
        except Exception as e:
            return JSONResponse({
                "text": "You must first connect your slack user\nTry /redmine help"
            })
        global redmine
        redmine = Redmine(user.redmine_url, key=user.redmine_key)

    commands = {
        "connect": connect,
        "todo": todo,
        "issue": issue,
        "help": help,
    }
    if params[0] not in commands:
        return JSONResponse({
            "text": "Ups! "+params[0]+" : Command not found"
        })
    return commands[params[0]](data, params)


def connect(data, params):
    try:
        User.objects.get(pk=data['user_id'])
    except Exception as e:
        try:
            redmine = Redmine(params[1], key=params[2])
            redmine.auth()
        except Redmine.exceptions.AuthError as e:
            return JSONResponse({
                "text": "Ups! Authentication fails: Invalid credentials. Sorry..."
            })
        user = User(slack_id=data['user_id'],redmine_url=params[1], redmine_key=params[2])
        user.save()
        return JSONResponse({
            "text": "Authentication success! "+data['user_name']+" you are ready to work!\nTry /redmine help"
        })
    return JSONResponse({
        "text": "User already connected. You are ready to work!\nTry \redmine help"
    })

def todo(data, params):

    return JSONResponse(list(redmine.issue.get(1, include='children,journals,watchers,relations,attachments,changesets')))
    # issues = []
    # for issue in redmine.issue.filter(project_id='sml'):
    #     issues.append({
    #         "id": issue.id,
    #         "subject": issue.subject,
    #         "priority": issue.priority.name,
    #         "tracker": issue.tracker.name,
    #         "status": issue.status.name,
    #         "hours": issue.estimated_hours if "estimated_hours" in dir(issue) else None,
    #         "description": issue.description})
    # return JSONResponse(issues)

def issue(data, params):
    issue_id = params[1]
    if not issue_id.isdigit():
        return JSONResponse({
            "text": "Ups! Invalid Issue ID"
        })
    if len(params) == 2:
        return issue_show(data, params)
    options = {
        "status": issue_status,
        "priority": issue_get_priority,
        "assignee": issue_get_assignee,
        "target": issue_get_target,
        "subtasks": issue_get_subtasks,
        "related": issue_get_related,
        "comments": issue_comments,
        "time": issue_logtime
    }
    if params[2] not in options:
        return JSONResponse({
            "text": "Ups! "+params[2]+" : Option not found.\n Try \redmine help"
        })
    return options[params[2]](data, params)

def issue_show(data, params):
    """
    An JSONResponse that returns an Issue.
    """
    pk = params[1]
    issue = redmine.issue.get(pk)
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nStatus: "+issue.status.name+"\nPriority: "+issue.priority.name+"\nEstimated hours: "+ (issue.estimated_hours if "estimated_hours" in issue else "-"),
        "attachments": [
            {
                "title": "Description",
                "text": issue.description
            },
        ]
    })

def issue_status(request, params):
    """
    Routes the status command options
    """
    try:
        return issue_set_status(params[1], params[3])
    except Exception as e:
        return issue_get_status(params[1])

def issue_get_status(pk):
    """
    An JSONResponse that retrun an Issie status
    """
    issue = redmine.issue.get(pk)
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nStatus: "+issue.status.name
    })

def issue_set_status(pk, status):
    """
    An JSONResponse that set and Issue status
    """
    statuses = redmine.issue_status.all()
    for s in statuses:
        if status.title() == s.name:
            issue = redmine.issue.get(pk)
            return JSONResponse({
                "text": issue.tracker.name+"#"+str(issue.id)+ (" Status changed to "+status.title()) if redmine.issue.update(pk,status_id=s.id) else "couldn't update the Status."
            })
    return JSONResponse({
        "text": status+" is not a valid Isssue Status",
        "attachments": [
            {
                "title": "Available Issue Statuses",
                "text": ", ".join([s.name for s in statuses])
            }
        ]
    })


def issue_get_priority(request, params):
    """
    An JSONResponse that returns an Issue priority
    """
    pk=params[1]
    issue = redmine.issue.get(pk)
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nPriority: "+issue.priority.name
    })


def issue_set_priority(request, params):
    """
    An JSONResponse that returns None :D
    """
    # Review if this could be implemented or not
    # It seems there is no Issue Priority Resource in PythonRedmine
    # Check if I could extend the library in order to have the Resource available
    return None


def issue_get_assignee(request, params):
    """
    An JSONResponse that returns an Issue assignee
    """
    pk=params[1]
    issue = redmine.issue.get(pk)
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nAssigne: "+ (issue.assigned_to.name if "assigned_to" in dir(issue) else "Not assigned")
    })


def issue_set_assignee(request, params):
    """
    An JSONResponse that return None :D
    """
    # Review if this could be implemented or not
    # It seems there is no Issue Assignee Resource in PythonRedmine
    # Check if I could extend the library in order to have the Resource available
    return None


def issue_get_target(request, params):
    """
    An JSONResponse that returns an Issue target
    """
    pk=params[1]
    issue = redmine.issue.get(pk)
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nTarget Version: "+ (issue.fixed_version.name if "fixed_version" in dir(issue) else "Not targeted")
    })


def issue_set_target(request, params):
    """
    An JSONResponse that returns None :D
    """
    # Review if this could be implemented or not
    # It seems there is no Issue Assignee Resource in PythonRedmine
    # Check if I could extend the library in order to have the Resource available
    return None


def issue_get_subtasks(request, params):
    """
    An JSONResponse that return an Issue subtasks
    """
    pk=params[1]
    issue = redmine.issue.get(pk,include='children')
    if not issue.children:
        return JSONResponse({
            "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nIt has no subtasks"
        })
    subtasks = []
    for task in issue.children:
        subtasks.append({
            "title": task.tracker.name+"#"+str(task.id)+" "+task.subject
        })
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nSubtasks:",
        "attachments": subtasks
    })

def issue_get_related(request, params):
    """
    An JSONResponse that returns an Issue related tasks
    """
    pk=params[1]
    issue = redmine.issue.get(pk,include='relations')
    if not issue.relations:
        return JSONResponse({
            "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nIt has no related issues"
        })
    related = []
    for rel in issue.relations:
        rel = redmine.issue.get(rel.issue_to_id)
        related.append({
            "title": rel.tracker.name+"#"+str(rel.id),
            "text": rel.subject
        })
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nRelated issues:",
        "attachments": related
    })

def issue_comments(request, params):
    pk=params[1]
    is_last=False
    try:
        opt=params[3]
        if opt=="add":
            try:
                comment=" ".join(opt[4])
            except:
                return JSONResponse({
                    "text": "Comment text missing!\nTry \redmine help"
                })
            return issue_add_comment(pk, comment)
        elif opt=="last":
            is_last=True
    except:
        return issue_get_comments(pk, is_last)

def issue_get_comments(pk, is_last):
    """
    An JSONResponse that returns an Issue comments
    """
    issue = redmine.issue.get(pk,include='journals')
    comments = []
    for journal in issue.journals:
        if "notes" in dir(journal) and journal.notes != "":
            comments.append({
                "title": str(journal.created_on)+" "+journal.user.name+" wrote:",
                "text": journal.notes
            })
    if not comments:
        return JSONResponse({
            "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nIt has no comments"
        })
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nComments:",
        "attachments": comments if not is_last else comments[-1]
    })


def issue_add_comment(pk, comment):
    """
    An JSONResponse that set an Issue comment
    """
    return JSONResponse({
        "text": "Adding a comment is not implemented yet... Sorry! "
    })

def issue_logtime(request, params):
    pk=params[1]
    try:
        if params[3] == "add" :
            hours=params[5]
            for n in range(4): params.remove(params[n])
            comment = " ".join(params)
            issue_add_logtime(pk,hours,comment)
    except:
        issue_get_logtime(pk)

def issue_get_logtime(pk):
    """
    An JSONResponse that returns an Issue time log
    """
    entries = redmine.time_entry.filter(issue_id=pk)
    timelog = []
    for entry in entries:
        timelog.append({
            "title": entry.user.name+" has spent "+str(entry.hours)+" hours on "+str(entry.created_on),
            "text": entry.comments
        })
    issue = redmine.issue.get(pk)
    if not timelog:
        return JSONResponse({
            "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nIt has no time entries"
        })
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+"\nTimelog:",
        "attachments": timelog
    })


def issue_add_logtime(pk, hours, comment):
    """
    An JSONResponse that set an Issue time log
    """
    issue = redmine.issue.get(pk)
    time_entry = redmine.time_entry.create(issue_id=pk, spent_on=timezone.now(), hours=hours, activity_id=9, comments=comment)
    return JSONResponse({
        "text": issue.tracker.name+"#"+str(issue.id)+ (" Time entry added") if time_entry else "couldn't add the time entry."
    })