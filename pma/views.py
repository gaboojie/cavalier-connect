from django.shortcuts import render,redirect
from events.models import Event
from myaccount.models import User
from django.contrib import messages
# Create your views here.

def pma_page(request):
    get_users = User.objects.all()
    event_map = {}
    #get users, for every user get event
    for user in get_users:
        user_events = Event.objects.filter(creator = user)
        if user not in event_map:
            event_map[user] = user_events
    context = {"event_map" : event_map}
    return render(request, "pma/pma.html", context)

def edit_event(request, user_id):
    user = User.objects.get(id = user_id)
    get_events = Event.objects.filter(creator =user)
    context = {"edit_events": get_events, "event_creator": user}
    return render(request, "pma/pma.html", context)

def delete_event(request):
    selected_events = request.GET.getlist('selected_events')

    if selected_events:
        events = Event.objects.filter(id__in=selected_events)
        for event in events: #delete each id
            try:
                event.delete()
                #print(f"event {event.id}: {event.title} has been deleted!")
            except Event.DoesNotExist:
                print(f"Event with ID {event.id} does not exist.")
    msg = f"You have successfully deleted an event or more!"
    messages.success(request, msg)
    return redirect('pma') 
