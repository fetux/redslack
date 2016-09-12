from django.utils import timezone
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
            params.update({'redmine_url': user.redmine_url})
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

    issues = redmine.issue.filter(assigned_to_id="me",status_id=2, limit=3)
    if not issues:
        issues = redmine.issue.filter(assigned_to_id="me",status_id=7,limit=3)
        if not issues:
            return JSONResponse({
                "text": "It seems there are not issues here."
            })
    todo = []
    for issue in issues:
        todo.append({
            "pretext": "<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">"+"\n_created by "+issue.author.name+"_",
            "title": "Description",
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
                    "title": "Assignee",
                    "value": (issue.assigned_to.name if "assigned_to" in dir(issue) else "Not assigned"),
                    "short": True
                },
                {
                    "title": "Estimated hours",
                    "value": (issue.estimated_hours if "estimated_hours" in dir(issue) else "-"),
                    "short": True
                },
            ],
            "mrkdwn_in": ["pretext", "text", "fields"]
        })
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_",
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
        return issue_show(params)
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

def issue_show(params):
    """
    An JSONResponse that returns an Issue.
    """
    issue = redmine.issue.get(params['issue_id'])
    for i in issue: print i
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">",
        "attachments": [
            {
                "title": "Description",
                "pretext": "_created by "+issue.author.name+"_",
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
                        "title": "Assignee",
                        "value": (issue.assigned_to.name if "assigned_to" in dir(issue) else "Not assigned"),
                        "short": True
                    },
                    {
                        "title": "Estimated hours",
                        "value": (issue.estimated_hours if "estimated_hours" in dir(issue) else "-"),
                        "short": True
                    },
                ],
                "mrkdwn_in": ["pretext", "text", "fields"]
            },
        ]
    })

def issue_status(params):
    """
    Routes the issue status command options
    """
    if not params['options']:
        return issue_get_status(params)

    return issue_set_status(params)


def issue_get_status(params):
    """
    An JSONResponse that retrun an Issie status
    """
    issue = redmine.issue.get(params['issue_id'])
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_",
        "attachments":[
            {
                "text": "<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">",
                "fields": [
                    {
                        "title": "Status",
                        "value": issue.status.name,
                        "short": True
                    },
                ],
                "mrkdwn_in": ["pretext", "text", "fields"]
            }
        ]
    })

def issue_set_status(params):
    """
    An JSONResponse that set and Issue status
    """
    statuses = redmine.issue_status.all()
    for s in statuses:
        if params['options'][0].title() == s.name:
            issue = redmine.issue.get(params['issue_id'])
            return JSONResponse({
                "text": "_/redmine "+params['text']+"_",
                "attachments":[
                    {
                        "text": "<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">",
                        "pretext": "_Status changed_" if redmine.issue.update(params['issue_id'],status_id=s.id) else "Couldn't update Issue. Sorry...",
                        "fields": [
                            {
                                "title": "Status",
                                "value": params['options'][0].title(),
                                "short": True
                            },
                        ],
                        "mrkdwn_in": ["pretext", "text", "fields"]
                    }
                ]
            } )
    return JSONResponse({
        "text": status+" is not a valid Isssue Status",
        "attachments": [
            {
                "title": "Available Issue Statuses",
                "text": ", ".join([s.name+" "+str(s.id) for s in statuses])
            }
        ]
    })


def issue_get_priority(params):
    """
    An JSONResponse that returns an Issue priority
    """
    issue = redmine.issue.get(params['issue_id'])
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_",
        "attachments":[
            {
                "text": "<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">",
                "fields": [
                    {
                        "title": "Priority",
                        "value": issue.priority.name,
                        "short": True
                    },
                ],
                "mrkdwn_in": ["pretext", "text", "fields"]
            }
        ]
    })


def issue_set_priority(params):
    """
    An JSONResponse that returns None :D
    """
    # Review if this could be implemented or not
    # It seems there is no Issue Priority Resource in PythonRedmine
    # Check if I could extend the library in order to have the Resource available
    return None


def issue_get_assignee(params):
    """
    An JSONResponse that returns an Issue assignee
    """
    issue = redmine.issue.get(params['issue_id'])
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_",
        "attachments":[
            {
                "text": "<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">",
                "fields": [
                    {
                        "title": "Assignee",
                        "value": (issue.assigned_to.name if "assigned_to" in dir(issue) else "Not assigned"),
                        "short": True
                    },
                ],
                "mrkdwn_in": ["pretext", "text", "fields"]
            }
        ]
    })


def issue_set_assignee(params):
    """
    An JSONResponse that return None :D
    """
    # Review if this could be implemented or not
    # It seems there is no Issue Assignee Resource in PythonRedmine
    # Check if I could extend the library in order to have the Resource available
    return None


def issue_get_target(params):
    """
    An JSONResponse that returns an Issue target
    """
    issue = redmine.issue.get(params['issue_id'])
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_",
        "attachments":[
            {
                "text": "<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">",
                "fields": [
                    {
                        "title": "Target",
                        "value": (issue.fixed_version.name if "fixed_version" in dir(issue) else "Not targeted"),
                        "short": True
                    },
                ],
                "mrkdwn_in": ["pretext", "text", "fields"]
            }
        ]
    })


def issue_set_target(params):
    """
    An JSONResponse that returns None :D
    """
    # Review if this could be implemented or not
    # It seems there is no Issue Assignee Resource in PythonRedmine
    # Check if I could extend the library in order to have the Resource available
    return None


def issue_get_subtasks(params):
    """
    An JSONResponse that return an Issue subtasks
    """
    issue = redmine.issue.get(params['issue_id'],include='children')
    if not issue.children:
        return JSONResponse({
            "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nSubtasks: None"
        })
    subtasks = []
    for task in issue.children:
        subtasks.append({
            "title": "<"+params['redmine_url']+"/issues/"+str(task.id)+"|"+task.tracker.name+"#"+str(task.id)+" "+task.subject+">"
        })
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nSubtasks:",
        "attachments": subtasks
    })

def issue_get_related(params):
    """
    An JSONResponse that returns an Issue related tasks
    """
    issue = redmine.issue.get(params['issue_id'],include='relations')
    if not issue.relations:
        return JSONResponse({
            "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nRelated Issues: None",
        })
    related = []
    for relation in issue.relations:
        if (relation.issue_to_id != int(params['issue_id'])):
            rel = redmine.issue.get(relation.issue_to_id)
            related.append({
                "title": "<"+params['redmine_url']+"/issues/"+str(rel.id)+"|"+rel.tracker.name+"#"+str(rel.id)+" "+rel.subject+">"
            })
        else:
            rel = redmine.issue.get(relation.issue_id)
            related.append({
                "title": "<"+params['redmine_url']+"/issues/"+str(rel.id)+"|"+rel.tracker.name+"#"+str(rel.id)+" "+rel.subject+">"
            })
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nRelated Issues:",
        "attachments": related
    })


def issue_comments(params):
    try:
        opt=params['options'][0]
        # if opt=="add":
        #     try:
        #         comment=" ".join(opt[4])
        #     except:
        #         return JSONResponse({
        #             "text": "Comment text missing!\nTry /redmine help"
        #         })
        #     return issue_add_comment(pk, comment)
        # elif opt=="last":
        if opt == "last":
            params.update({"is_last": True})
            return issue_get_comments(params)
    except:
        return issue_get_comments(params)

def issue_get_comments(params):
    """
    An JSONResponse that returns an Issue comments
    """
    issue = redmine.issue.get(params['issue_id'],include='journals')
    comments = []
    for journal in issue.journals:
        if "notes" in dir(journal) and journal.notes != "":
            comments.append({
                "pretext": "_"+str(journal.created_on)+" "+journal.user.name+" wrote:_",
                "text": journal.notes,
                "mrkdwn_in": ["pretext", "text"]
            })
    if not comments:
        return JSONResponse({
            "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nComments: None"
        })
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nComments:",
        "attachments": comments if not "is_last" in params else [comments[-1]]
    })


# def issue_add_comment(pk, comment):
#     """
#     An JSONResponse that set an Issue comment
#     """
#     return JSONResponse({
#         "text": "Adding a comment is not implemented yet... Sorry! "
#     })

def issue_logtime(params):
    try:
        if params['options'][0] == "add":
            params.update({"hours": params['options'][1]})
            for n in range(2): params['options'].pop(0)
            params.update({"comment": " ".join(params['options'])})
            return issue_add_logtime(params)
    except:
        return issue_get_logtime(params)

def issue_get_logtime(params):
    """
    An JSONResponse that returns an Issue time log
    """
    entries = redmine.time_entry.filter(issue_id=params['issue_id'])
    timelog = []
    for entry in entries:
        timelog.append({
            "pretext": "_"+str(entry.created_on)+" "+entry.user.name+" has spent *"+str(entry.hours)+" hours:*_",
            "text": entry.comments,
            "mrkdwn_in": ["pretext", "text"]
        })
    issue = redmine.issue.get(params['issue_id'])
    if not timelog:
        return JSONResponse({
            "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nTimelog: None",
        })
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nTimelog:",
        "attachments": timelog
    })


def issue_add_logtime(params):
    """
    An JSONResponse that set an Issue time log
    """
    issue = redmine.issue.get(params['issue_id'])
    time_entry = redmine.time_entry.create(issue_id=params['issue_id'], hours=params['hours'], activity_id=9, comments=params['comment'])
    if not time_entry:
        return JSONResponse({
            "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\nCouldn't add entry",
        })
    return JSONResponse({
        "text": "_/redmine "+params['text']+"_\n"+"<"+params['redmine_url']+"/issues/"+str(issue.id)+"|"+issue.tracker.name+"#"+str(issue.id)+" "+issue.subject+">\n_New Entry Time added:_",
        "attachments": [
            {
                "pretext": "_"+str(time_entry.created_on)+" "+time_entry.user.name+" has spent *"+str(time_entry.hours)+" hours*:_",
                "text": time_entry.comments,
                "mrkdwn_in": ["pretext", "text"]
            }
        ]
    })

def help(params = None):
    """
    An JSONResponse that displays the command help
    """
    return JSONResponse({
        "text": """_/redmine help_\n*How to use: /redmine <command> [options]*

        *Lets you interact with your Redmine application.*

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


