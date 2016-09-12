from django.db import IntegrityError
from rest_framework.decorators import api_view
from redmine import *
from models import User
from utilities import *

redmine = None

@api_view(['POST'])
def router(request):
    """
    API entry point that routes outside world requests
    """
    params = {}
    for k,p in request.POST.iteritems():
        params.update({k: p})
    text = request.POST['text'].split()
    try:
        params.update({'command': text.pop(0)})
        params.update({'options': text})
        non_auth_commands = ['connect', 'help']
        if params['command'] not in non_auth_commands:
            try:
                user = User.objects.get(slack_id=params['user_id'])
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
        if params['command'] not in commands:
            return JSONResponse({
                "text": "Ups! "+params['command']+" : Command not found"
            })
        return commands[params['command']](params)
    except IndexError as e:
        return help()

print

def connect(params):
    try:
        user = User.objects.get(pk=params['user_id'])
    except Exception as e:
        try:
            redmine = Redmine(params['options'][0], key=params['options'][1])
            redmine.auth()
            user = User(slack_id=params['user_id'],redmine_url=params['options'][0], redmine_key=params['options'][1])
            print user.save()
            print user
        except IntegrityError as e:
            return JSONResponse({
            "text": "Ups! Redmine key "+params['options'][1]+" already connected to another Slack User. Sorry..."
            })
        except AuthError as e:
            return JSONResponse({
            "text": "Ups! Authentication fails: Invalid credentials. Sorry..."
            })
        return JSONResponse({
            "text": "Authentication success! "+params['user_name']+" you are ready to work!\nTry /redmine help"
        })
    return JSONResponse({
        "text": "User already connected. You are ready to work!\nTry /redmine help"
    })

def todo(params):

    issues = redmine.issue.filter(assigned_to_id="me",status_id=2)
    if not issues:
        issues = redmine.issue.filter(assigned_to_id="me",status_id='closed',limit=3)
        if not issues:
            return JSONResponse({
                "text": "It seems there are not issues here."
            })
    todo = []
    for issue in issues:
        todo.append({
            "id": issue.id,
            "subject": issue.subject,
            "priority": issue.priority.name,
            "tracker": issue.tracker.name,
            "status": issue.status.name,
            "hours": issue.estimated_hours if "estimated_hours" in dir(issue) else None,
            "description": issue.description})
    return JSONResponse({
        "text": "To-Do",
        "attachments": todo
    })


def issue(params):
    # Extract issue_id should be fisrt element in options, and add it to params so we could send it easily to the following method
    params.update({"issue_id": params['options'].pop(0)})
    if not params['issue_id'].isdigit():
        return JSONResponse({
            "text": "Ups! Invalid Issue ID"
        })
    # If there no left options is just asking /redmine issue <id>
    if not params['options']:
        return issue_show(params['issue_id'])
    # If there are more options, lets route them
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
    # Extract following option and check if it is an option available
    option = params['options'].pop(0)
    if option not in options:
        return JSONResponse({
            "text": "Ups! "+option+" : Option not found.\n Try /redmine help"
        })
    return options[option](params)

def issue_show(pk):
    """
    An JSONResponse that returns an Issue.
    """
    issue = redmine.issue.get(pk)
    return JSONResponse({
        "text": "<http://redmine.smarterlith.net/issues/"+str(pk)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">",
        "attachments": [
            {

                "title": "",
                "text": issue.description,
                "fields":[
                    {
                        "title": "Status",
                        "value": issue.status.name,
                        "short": True
                    },
                    {
                        "title": "Priority",
                        "value": issue.priority.name,
                        "short": True
                    },
                    {
                        "title": "Estimated hours",
                        "value": (issue.estimated_hours if "estimated_hours" in issue else "-"),
                        "short": True
                    },
                ]
            },
        ]
    })

def issue_status(params):
    """
    Routes the issue status command options
    """
    if not params['options']:
        return issue_get_status(params['issue_id'])

    return issue_set_status(params['issue_id'], params['options'][0])


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
                "text": ", ".join([s.name+" "+str(s.id) for s in statuses])
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
                    "text": "Comment text missing!\nTry /redmine help"
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

def issue_logtime(params):
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

def help(params = None):
    """
    An JSONResponse that displays the command help
    """
    return JSONResponse({
        "text": """*How to use: /redmine <command> [options]*

        *Let you interact with your Redmine application.*

        Available_commands:

        */redmine connect <redmine-url> <user-key>*

            This will connect your Slack account with your Redmine account.
            <redmine-url> should be the URL of your Redmine application.
            <user-key> should be your token that you can find it in 'My Account' at Redmine's

        */redmine todo*

            This will return what you have to do... According Redmine ;)

        */redmine issue <id>*

            This will return available information of an Issue

        */redmine issue <id> status [status]*

            This will return or set the status of an Issue.
            e.g: `/redmine issue 5420 status` will return the status of Issue#5420
            e.g: `/redmine issue 5420 status resolved` will set the status of Issue#5420 to `Resolved`

        */redmine issue <id> priority*

            This will return the priority of an Issue.

        */redmine issue <id> assignee*

            This will return the Assignee of an Issue

        */redmine issue <id> target*

            This will return the Target of an Issue.

        */redmine issue <id> subtasks*

            This will return the Subtasks of an Issue.

        */redmine issue <id> related*

            This will return the Related Issues of an Issue.

        */redmine issue <id> comments*

            This will return all the Comments of an Issue.

        */redmine issue <id> comments last*

            This will return the last Comment of an Issue.

        */redmine issue <id> time*

            This will return the logged hours in an Issue

        */redmine issue <id> time add <hours> <comment>*

            This will log the hours in the Issue with the comment specified.
        """
    })


