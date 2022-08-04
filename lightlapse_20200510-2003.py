# -*- coding: utf-8 -*-
"""
For managing plant grow lights & taking timelapses.

Needs a way to select path for timelapse from UI, allow user to input pattern for filenames?

Could use some theme-ing, menu-ing,
Affected by daylight savings? may cause an hour offset for one day,
twice per year until we decide as a country to stop doing silly things.
          ___________________________________
         |Good thing this machine is offline!|
_   _   _l/```````````````````````````````````
 \(`u`)/
   |_|
   / \

Need to add camera rotation setting.
Using pathlib also probably a good idea.
Using logging module also probably a good idea.
Would be cool to make timer automatically update when a combobox is changed?
Pipe? Queue?

"""

import os
import atexit
from random import randrange
from datetime import datetime, timedelta
from time import sleep
from multiprocessing import *
from functools import partial
from tkinter.ttk import Combobox
from tkinter import Tk, IntVar, Label, Entry, Button, Checkbutton, Frame, Scale, SUNKEN, RAISED

def log(msg):
    """ d e b u g """
    if not windows:
        af = open('/home/pi/code/python/log_3.txt','a')
        af.write('\n' + msg)
        af.close()
    print(msg)

try:
    windows = False
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    from picamera import PiCamera
except Exception:
    windows = True
    log('not running on rpi, setting flag...')

hrs = [('0' + str(hr))[-2:] for hr in range(24)][::]
mins = [('0' + str(min_))[-2:] for min_ in range(60)][::]
pin = 17
procs = set()



log(f'!session initialized at {datetime.now()}')

def check_clock():
    """ logs active processes & checks tk interface against system clock,
        returns string:bool for on_time & string:Datetime for now,start,stop """
    log(f'active processes:\n{procs}')

    now = datetime.now()
    start = datetime(now.year, now.month, now.day, int(hr_cb.get()), int(min_cb.get()))
    stop = datetime(now.year, now.month, now.day, int(stop_hr_cb.get()), int(stop_min_cb.get()))
    weirdtimes = stop < start
    if weirdtimes:
        if now < stop: on_time = True # now-6:20, stop-6:30, start-6:35
        elif now < start: on_time = False # now-6:32, stop-6:30, start-6:35
        else: on_time = True # now-6:37, stop-6:30, start-6:35
    else:
        on_time = start <= now < stop # now-?, stop-19:00, start-07:00 

    r_m = int(r_m_slide.get())

    log(f'\nnow: {now}\n')
    log(f'\nstart: {start}\n')
    log(f'\nstop: {stop}\n')
    log(f'\non_time: {on_time}\n')

    return {'on_time': on_time, 'now': now, 'start': start, 'stop': stop}

def light_timer():
    """ checks if it is time for the light to be on or off, takes appropriate action.
        sleeps until next action is required. """

    kill_lights()
    atexit.register(kill_lights)

    if not windows:
        log('performing gpio setup...')
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)

    while True:

        r_m = int(r_m_slide.get())

        clock = check_clock()

        if clock['on_time']:
            log('Sending on signal to GPIO...')
            if not windows:
                GPIO.output(pin, GPIO.HIGH) # light on

            log('calculating sleep time...')
            sleep_time = wait_until(clock['now'], clock['stop'], r_m)
            log(f'!light turned on;\nchecking again in {sleep_time} sec == {sleep_time / 60 / 60} hrs...') 
            sleep(sleep_time)

        else:
            log('Sending off signal to GPIO...')
            if not windows:
                    GPIO.output(pin, GPIO.LOW) # light off
            
            log('calculating sleep time...')
            sleep_time = wait_until(clock['now'], clock['start'], r_m)
            log(f'outside "on" times;\nchecking again in {sleep_time} sec == {sleep_time / 60} min == {sleep_time / 60 / 60} hrs...') 
            sleep(sleep_time)


def wait_until(fr, when, r_m=0):
    """
    determines how long to wait for next on/off, returns int never < 1,
    adds a random number of seconds between 0 and r_m to avoid unwanted detection of automation
    (default if no value is passed for r_m is to add no random seconds to the return)
    """
    if r_m:
        to_add = randrange(0,(60*r_m),1)
    else:
        to_add = 0

    sleep_time = (when - fr).seconds
    log(f'raw sleeptime: {sleep_time}')
    sleep_time += to_add
    log(f'altered sleeptime: {sleep_time}')
    if sleep_time < 1:
        log('sleeptime<1') # prevents program-breaking infinitely just-too-short sleeps
        return 1
    return sleep_time



def cleanup():
    """ Prepares GPIO & Tk for program exit """
    log('cleanup')
    kill_lights()
    kill_procs()
    root.destroy()

def manual_on():
    """ """
    kill_lights()
    atexit.register(kill_lights)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH) # light on  
    log(f'!manual on initialized at {datetime.now()}')

def kill_lights():
    """ Kills light & cleans up GPIO """
    if windows:
        log('windows')
    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW) # light off
        GPIO.cleanup()
        log('kill_lights')

def ind_txt():
    """ determines text for light timer indicator label, returns full label text as str """
    now = datetime.now()
    start = datetime(now.year, now.month, now.day, int(hr_cb.get()), int(min_cb.get()))
    stop = datetime(now.year, now.month, now.day, int(stop_hr_cb.get()), int(stop_min_cb.get()))
    if start < stop:
        daytime = int(stop_hr_cb.get()) + (int(stop_min_cb.get()) / 60) - int(hr_cb.get()) - (int(min_cb.get()) / 60)
    else:
        daytime = 24 - abs(int(stop_hr_cb.get()) + (int(stop_min_cb.get()) / 60) - int(hr_cb.get()) - (int(min_cb.get()) / 60))
    
    return f'< Active ; {round(daytime, 3)}'

def move_ind(indicator, widget):
    """ grids indicator widget to buttons in the clumsiest dumbest way possible """
    if widget['text'] == 'Timer':
        indicator.config(text=ind_txt())
        indicator.grid(row=5, column=3)
    elif widget['text'] == 'Manual Off':
        indicator.config(text='< Active')
        indicator.grid(row=6, column=3)
    elif widget['text'] == 'Manual On':
        indicator.config(text='< Active')
        indicator.grid(row=7, column=3)

def timelapse():
    """
    Shoots a frame at <res[0]> x <res[1]> every <inter> minutes.
    Skips any shots between <start> and <stop> if 
    """

    if windows:
        log('windows, timelapse ignored')
    else:
        cam = PiCamera()
        cam.rotation = 90
        atexit.register(cam.close)
        log('timelapse started')

        # setting exposure
        def set_exposure():
            """ Should put these settings in a menu """
            cam.iso = 100
            sleep(2)
            cam.shutter_speed = cam.exposure_speed
            cam.exposure_mode = 'off'
            g = cam.awb_gains
            cam.awb_mode = 'off'
            cam.awb_gains = g
            log('camera exposure set')
        set_exposure()

        res = (int(resx.get()),int(resy.get()))
        cam.resolution = (res[0], res[1])
        log(f'resolution set at {res}')
        
        inter = int(interval.get())
        log(f'interval set at {inter}')

        now = datetime.now()
        start = datetime(now.year, now.month, now.day, int(hr_cb.get()), int(min_cb.get()))
        stop = datetime(now.year, now.month, now.day, int(stop_hr_cb.get()), int(stop_min_cb.get()))
        
        thisfolder = '/home/pi/Desktop/timelapses/continuous/'
        log(f'frames will be saved to {thisfolder}')

        if not os.path.exists(thisfolder):
            log(f'{thisfolder} does not exist, making...')
            os.makedirs(thisfolder, exist_ok=True)
            log(f'{thisfolder} made!')

        for filename in cam.capture_continuous(thisfolder + 'img{timestamp:%y%m%d-%H%M%S}.png'):
            log(f'captured {filename}')
            sleep(10)
            if restrict.get() and os.stat(filename).st_size < 1000000:
                log(f'light is not on, deleting {filename}...')
                os.remove(filename)
                log(f'{filename} deleted')
            sleep(60 * inter)

def spawn_proc(target):
    """
    Accepts individual functions or iterables of functions,
    starts a process for each function passed & adds the process to list procs.
    """
    global procs
    try:
        len(target)
        for i in target:
            spawn_proc(i)
    except TypeError:
        log(f'forking a {target.__name__}')
        proc = Process(target=target)
        proc.name = target.__name__[:]
        procs.add(proc)
        proc.start()
        log(f'{target.__name__} started')

def kill_procs(target=0):
    """
    stops all procs whose names match the input string <target>,
    if target is not specified kills all procs. Probably a better way to do this.
    """
    log(f'kill_procs called w/ target: {target}')
    global procs
    killit = False
    for proc in procs:
        if isinstance(target, int):
            killit = True
        if not killit:
            if proc.name == target.__name__:
                killit = True
        if killit:
            log(f'killing a {proc.name}')
            procs.remove(proc)
            proc.terminate()
            log(f'{proc.name} killed')
            break

def lapse_btns(status):
    """ toggles timelapse buttons. <status> indicates whether the timelapse
        is being turned on or off. """
    if status:
        start_timelapse['state'] ='disabled'
        stop_timelapse['state'] = 'normal'
        
    else:
        start_timelapse['state'] = 'normal'
        stop_timelapse['state'] = 'disabled'

def helpwindow():
    """ this is more or less just a test """
    helpwin = Tk()
    contents = str('The "r" slider tells the light timer\n'
                 + 'between 0 and what number of minutes\n'
                 + 'to randomly select a whole number from.\n'
                 + 'this number of minutes are then added\n'
                 + 'to the day or night cycle at each transition.')
    contlabel = Label(helpwin, text=contents)
    contlabel.pack()
    helpwin.mainloop()

log(f'*new session started {datetime.now()}\n\n') 
timer_birthdate = datetime.now()

# Some day I will clean this up and make a config file
root = Tk()
root.title('LightLapse')
root.geometry('460x280')
timeframe = Frame(root)
stop_timeframe = Frame(root)
menuframe = Frame(root)
helpmenu = Button(menuframe, text='help', command=helpwindow)

r_m_label = Label(root, text='r:')
r_m_slide = Scale(root, from_=60, to=0)

hr_cb = Combobox(timeframe, values=hrs, width=3)
hr_cb.set('18')
colon = Label(timeframe, text=':')
min_cb = Combobox(timeframe, values=mins, width=3)
min_cb.set('00')
hr_lbl = Label(root, text="Start Time:")

stop_hr_lbl = Label(root, text="Stop Time:")
stop_hr_cb = Combobox(stop_timeframe, values=hrs, width=3)
stop_hr_cb.set('13')
stop_colon = Label(stop_timeframe, text=':')
stop_min_cb = Combobox(stop_timeframe, values=mins, width=3)
stop_min_cb.set('00')

indicator = Label(root, text='< Active', width=12)

# sorry
go = Button(root, text="Timer", command=lambda: [f() for f in [partial(kill_procs, target=light_timer), partial(spawn_proc, target=light_timer), partial(move_ind, indicator, go)]])
stop = Button(root, text="Manual Off", command=lambda: [f() for f in [kill_lights, partial(kill_procs, target=light_timer), partial(move_ind, indicator, stop)]])
override = Button(root, text="Manual On", command=lambda: [f() for f in [partial(kill_procs, target=light_timer), manual_on, partial(move_ind, indicator, override)]], width=stop['width'])

r_m_label.grid(row=1, column=0)
r_m_slide.grid(row=2, column=0, rowspan=5)

hr_cb.grid(row=1, column=1)
colon.grid(row=1, column=2)
min_cb.grid(row=1, column=3)

stop_hr_cb.grid(row=1, column=1)
stop_colon.grid(row=1, column=2)
stop_min_cb.grid(row=1, column=3)

helpmenu.grid(row=0, column=0)
menuframe.grid(row=0, column=0)
hr_lbl.grid(row=1, column=2)
timeframe.grid(row=2, column=2)

stop_hr_lbl.grid(row=3, column=2)
stop_timeframe.grid(row=4, column=2)

go.grid(row=5, column=2, padx=5, pady=(10, 5))

stop.grid(row=6, column=2, padx=5, pady=5)
indicator.grid(row=6, column=3)

override.grid(row=7, column=2, padx=5, pady=(5, 10))

resx = Entry(root, width=8)
resx.insert(0, '1920')
resy = Entry(root, width=8)
resy.insert(0, '1080')
l_res = Label(root, text='Dimensions:')
l_resx = Label(root, text='x: ')
l_resy = Label(root, text='y: ')
l_res.grid(row=1, column=4)
l_resx.grid(row=2, column=4, sticky='W')
resx.grid(row=2, column=4)
l_resy.grid(row=3, column=4, sticky='W')
resy.grid(row=3, column=4)

interval = Entry(root, width=8)
interval.insert(0, '16')
l_interval = Label(root, text='Interval (minutes): ')
interval.grid(row=5, column=4, pady=0)
l_interval.grid(row=4, column=4)

l_restrict_tl = Label(root, text='Restrict timelapse to light times:')
restrict = IntVar()
restrict_tl = Checkbutton(root, variable=restrict)
start_timelapse = Button(root, text='Run timelapse')
stop_timelapse = Button(root, text='Stop timelapse')
# sorry
start_timelapse.config(command=lambda: [f() for f in [kill_procs, partial(spawn_proc, target=[timelapse, light_timer]), partial(move_ind, indicator, go), partial(lapse_btns, 1)]])
stop_timelapse.config(command=lambda: [f() for f in [partial(kill_procs, target=timelapse), partial(lapse_btns, 0)]])
start_timelapse['state'] = 'normal'
stop_timelapse['state'] = 'disabled'
start_timelapse.grid(row=6, column=4)
stop_timelapse.grid(row=7, column=4)
l_restrict_tl.grid(row=8, column=1, columnspan=6, sticky='W')
restrict_tl.select()
restrict_tl.grid(row=8, column=4)



root.protocol("WM_DELETE_WINDOW", cleanup)
root.mainloop()

log(f'*session ended {datetime.now()}\n\n') 
