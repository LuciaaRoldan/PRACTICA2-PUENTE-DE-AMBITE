"""
Solution to the one-way tunnel
LUCÍA ROLDÁN RODRÍGUEZ.
VERSIÓN 2.
Cumple la seguridad y carece de inanición pero podría darse 
deadlock. Mostrémoslo con un ejemplo: si hay coches en sentido norte pasando 
por la carretera en cuanto pase el primero cedería el turno a 1 pero si cs_waiting = 0
en el tiempo en el que terminan de pasar los coches que había en la carretera se pueden almacenar
cn_waiting >0 y ped_waiting>0 y como el turno = 1 ninguno podría pasar hasta que llegase un coche
en sentido sur que quisiera pasar, si hubieran terminado de consumir este tipo de coches o no llegase uno
en mucho tiempo causaría deadlock. Para ello en la siguiente versión comprobamos que existan coches esperando 
antes de ceder el turno.

"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

#directions
SOUTH = 1
NORTH = 0

NCARS = 100
NPED = 10
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRIAN = (30, 10) # normal 1s, 0.5s

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        
        self.cn = Value('i', 0) # Número de coches en sentido norte dentro del puente.
        self.cs = Value('i', 0) # Número de coches en sentido sur dentro del puente.
        self.ped = Value('i', 0) # Número de peatones dentro del puente.
        
        self.cn_waiting = Value('i',0) # Número de coches en sentido norte esperando a entrar.
        self.cs_waiting = Value('i',0) # Número de coches en sentido sur esperando a entrar.
        self.ped_waiting = Value('i',0) # Número de peatones esperando a entrar.
        
        self.turn = Value('i',0) #Turnos de paso. 
        # Turno = 0 marca preferencia de paso a los coches en sentido norte.
        # Turno = 1 marca preferencia de paso a los coches en sentido sur.
        # Turno = 2 marca preferencia de paso a los peatones.
        
        self.nocars = Condition(self.mutex) # Condición que regula el paso de peatones.
        self.nocn_noped = Condition(self.mutex) # Condición que regula el paso de coches en sentido sur.
        self.nocs_noped = Condition(self.mutex) # Condición que regula el paso de coches en sentido norte.
        
    def carnoth_mayenter(self):
        return (self.cs.value == 0) and (self.ped.value == 0) and\
                (self.turn.value == 0 or (self.cs_waiting.value == 0 and self.ped_waiting.value == 0))
    def carsouth_mayenter(self):
        return (self.cn.value == 0) and (self.ped.value == 0) and\
                (self.turn.value == 1 or (self.cn_waiting.value == 0 and self.ped_waiting.value == 0))
    def pedestrian_mayenter(self):
        return (self.cs.value == 0) and (self.cn.value == 0) and\
                (self.turn.value == 2 or (self.cn_waiting.value == 0 and self.cs_waiting.value == 0))
                
    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        
        if direction == 0:
            self.cn_waiting.value += 1
            self.nocs_noped.wait_for(self.carnoth_mayenter)
            self.cn_waiting.value -= 1
            self.cn.value += 1            
            
        else:
            self.cs_waiting.value += 1
            self.nocn_noped.wait_for(self.carsouth_mayenter)
            self.cs_waiting.value -= 1
            self.cs.value += 1
            
        self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        
        self.mutex.acquire()
        
        if direction == 0:
            self.cn.value -= 1
            self.turn.value = 1
            if self.cn.value == 0 :
                self.nocars.notify_all()
                self.nocn_noped.notify_all()
            
        else:
            self.cs.value -= 1
            self.turn.value = 2
            if self.cs.value == 0 :
                 self.nocars.notify_all()
                 self.nocs_noped.notify_all()
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.ped_waiting.value += 1
        self.nocars.wait_for(self.pedestrian_mayenter)
        self.ped_waiting.value -= 1
        self.ped.value += 1
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.ped.value -= 1
        self.turn.value = 0
        if self.ped.value == 0:
            self.nocn_noped.notify_all()
            self.nocs_noped.notify_all()
        self.mutex.release()

    def __repr__(self) -> str:
        return  f"M : <cnor:{self.cn.value}, csur:{self.cs.value}, pedestrian:{self.ped.value}, cnor_waiting:{self.cn_waiting.value}, csur_waiting:{self.cs_waiting.value}, pedestrian_waiting:{self.ped_waiting.value},  turn:{self.turn.value}>"

def delay_car_north() -> None:
    a = random.normalvariate(1,0.5)
    time.sleep(max(a,.0))

def delay_car_south() -> None:
    a = random.normalvariate(1,0.5)
    time.sleep(max(a,.0))

def delay_pedestrian() -> None:
    time.sleep(random.normalvariate(30,10))

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    print(f"pedestrian {pid} out of the bridge. {monitor}")



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()

def gen_cars(direction: int, time_cars, monitor: Monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/time_cars))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars_north = Process(target=gen_cars, args=(NORTH, TIME_CARS_NORTH, monitor))
    gcars_south = Process(target=gen_cars, args=(SOUTH, TIME_CARS_SOUTH, monitor))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars_north.start()
    gcars_south.start()
    gped.start()
    gcars_north.join()
    gcars_south.join()
    gped.join()


if __name__ == '__main__':
    main()

