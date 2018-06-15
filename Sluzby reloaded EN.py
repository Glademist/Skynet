"""Program na generování služeb pro chirugii Krajské nemocnice Liberec
   Autor programu: MUDr. Alexandr Škaryd
   Ver.: SKYNET v 0.5
   Do not spread this code.

   The script first loads all the days in the current "timespan".
   It counts all workdays, weekends and calculates optimal counts for each worker.
   Then it loads up all preferences from each worker and assignd letters to workers.
   So each worker is only a single letter like A B or C. The reason is to keep
   better oversight over the sequences generated through genetic algorithm.

   Config files for each worker in this format.
   1 - number of workdays or X (for average)
   2 - number of weekends or X
   3 - employment (as in someone can have only 50% employment and thus half the workdays and weekends)
   4 - minimal interval between shifts
   5 - number of days s indexem 1 - deprecated 
   6 - number of days s indexem 1.125 - deprecated
   7 - number of days s indexem 1.25 - not used atm
   8 - number of days s indexem 1.3 - not used atm
   9 - number of days s indexem 1.37 - not used atm
   12 - list of days on which the workers WANTS to work
   13 - keyword NEMUZE marking the end of WANTED days
   14 - list of days on which the worker DOESNT want to work
   
   file override.txt contains
   Date and Worker name to override any options
   """

#Imports
from datetime import timedelta, datetime
import random, statistics, copy

#Constants
WorkersFilename = "docold.txt"
OverrideFilename = "overold.txt"
SourceAbeceda = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
Population_count = 5 #5
PopulationSize = 100 #200
MutationRate = 20 #percentage of mutations, possibly make it variable in time / cycle
CrossoverRate = 50 #percentage of crossover, atm very stupid since using RANDOM and not actual transposition
Cycles = 200 #200
ElitePercentage = 10 #percentage of seeded individuals from the Elite specimens.
Penalty_interval = 2 #300
Penalty_weekend = 1 #150
Penalty_fridays = 1 #50
Penalty_count = 2 #1000
Penalty_critical = 3
Theoretical_fitness = Penalty_interval + Penalty_weekend + Penalty_fridays + Penalty_count + Penalty_critical+1

#Classes
class Worker(object): #the worker variable containing all Letter which is assigned. Limits on workdays count. Array of desired and undesired days to work on.
    def __init__(self, letter, employment, min_interval, i1, i125, i25, i3, i37, limit_workday, limit_weekend, desired_duty = [], undesired_duty = []):
        self.letter = letter
        self.employment = employment
        self.min_interval = min_interval
        self.i1 = i1
        self.i125 = i125
        self.i25 = i25
        self.i3 = i3
        self.i37 = i37
        self.limit_workday = limit_workday
        self.limit_weekend = limit_weekend
        self.desired_duty = desired_duty
        self.undesired_duty = undesired_duty
        

    def description(self):
        pass

class DayOfLife(object): #object for storing all data about a single day in calendar, index is based on day, Monday Tuesday Wednesday is 1.125, Thursday 1, Friday 1.25, Saturday 1.37, Sunday 1.3
    def __init__(self, index, worker, possible_duty = []):
        self.index = index
        self.possible_duty = possible_duty
        self.worker = worker

    def description(self):
        pass

class Population(object): #object for holding entire popuplation, with max and min fitness counted and array of all sequences, where sequence is a string of people working on each day in a sequence
    def __init__(self, maxfitness, minfitness, sequences = []):
        self.sequences = sequences
        self.maxfitness = maxfitness
        self.minfitness = minfitness

    def description(self):
        pass

class Sequence(object): #object for storing a sequence with counted fitness stored, a sequence looks like "ABAGEDHAB" which means first letter is first day in timespan and B the last day. Each letter is one worker.
    def __init__(self, fitness, workers):
        self.workers = workers
        self.fitness = fitness

    def description(self):
        pass

#Functions
def load_worker_sources(filename):
    #loads up all workers from files based on a superfile containing all names, it should receive information and save it into a data type
    with open(filename) as f:
        content = f.readlines()
        content = [x.strip() for x in content]
        
    workers = {}

    #for each name in the superfile we open a file with appropriate name and get the data.
    for x in content:
        #create new worker variable
        # (letter, employment, min_interval, i1, i125, i25, i3, i37, limit_workday, limit_weekend, desired_duty = [], possible_duty = [])
        loading_worker = Worker(0,0,0,0,0,0,0,0,0,[],[])
        #generate file name
        filename = x + ".txt"
        #one by one open all files and fill the workers into a dictionary
        with open(filename) as f:
            loading_worker.limit_workday = f.readline().strip()
            loading_worker.limit_weekend = f.readline().strip()
            loading_worker.employment = f.readline().strip()
            loading_worker.min_interval = f.readline().strip()
            loading_worker.i1 = f.readline().strip()
            loading_worker.i125 = f.readline().strip()
            loading_worker.i25 = f.readline().strip()
            loading_worker.i3 = f.readline().strip()
            loading_worker.i37 = f.readline().strip()
            source = f.readlines()
            source = [x.strip() for x in source] #pull apart for single data entries
            desires =  []
            desiresnot = []
            i = 0
            while i < len(source):
                if source[i] != "NEMUZE": #nemuze is a keyword in the config file, it means "Is UNABLE TO"
                    desires.append(source[i])
                if source[i] == "NEMUZE":
                    i+=1
                    break
                i+=1
            while i < len(source):
                desiresnot.append(source[i])
                i+=1
            loading_worker.desired_duty = desires
            loading_worker.undesired_duty = desiresnot
            workers[x] = loading_worker
    
    currentAbeceda = SourceAbeceda[:len(workers)] 

    #we assign each worker his letter from the alphabet = abeceda
    i = 0
    for key in workers:
        workers[key].letter = currentAbeceda[i]
        i += 1
    
    return [workers, currentAbeceda]

def calendar_interval_get(): #set up for calendar timespan, until final version i dont want user input
    start_rok = int(2018)
    start_mesic= int(7)
    start_den = int(1)
    end_year = int(2018)
    end_month = int(7)
    end_day = int(31)
    first_day = datetime(start_rok, start_mesic, start_den)
    last_day = datetime(end_year, end_month, end_day)
    return (first_day, last_day)

def calendar_genesis(first_day,last_day):
    #we create the list of days we want to work on, entire calendar, time span
    dateList = {} 
    day_count = (last_day - first_day).days +1

    #this really speeds up assigning of indexes to days in the for cycle below, it is a solution found online
    indexes = {"1" : float(1.125), "2" : float(1.125),"3" : float(1.125),"4" : float(1.01),"5" : float(1.25),"6" : float(1.37),"7" : float(1.3)}

    #the cycle parses each day in the calendar and assigns index, creates a new day, assigns date and adds the new day into the list
    for single_date in (first_day + timedelta(n) for n in range(day_count)):
        index = indexes.get(str(single_date.isoweekday()))
        new_day = DayOfLife(index,[])
        dateList[single_date.strftime('%Y-%m-%d')] = new_day
        
    #override holidays - loads up file with holidays which change the generic days into saturdays or sundays depending on the holiday location in a week
    content = {}
    with open("svatky.txt") as f:
        i = 0
        for line in f:
            #we split each line into date and index
            splitLine = line.split()
            content[(splitLine[0])] = " ".join(splitLine[1:])
            i += 1

    #we go through the calendar and find all days that need to be overriden and overwrite their index
    for key in dateList:
        if key in content:
            dateList[key].index = float(content[key]) # tohle by melo stacit

    return dateList, months

def calendar_availability(kalendar_source,workers_sources):
    #parse all calendar and add the worker letter allways except when he desires not 
    calendar = kalendar_source

    workers = workers_sources
    for day in calendar:
        calendar[day].possible_duty = [] #WHYYYYYYYY!!!!!!???????? doesnt it work without setting up?
        for key in workers:
            if day not in workers[key].undesired_duty:
                calendar[day].possible_duty.append(workers[key].letter)

    #pass through all workers based by their desire to work and append doctors who want to work on each day
    #first we clean up the day, then put in the workers
    for day in calendar:
        first = True
        den = calendar.get(day)
        for key in workers:
            if day in workers[key].desired_duty:
                if first == True:
                    den.possible_duty = []
                    den.possible_duty.append(workers[key].letter)
                    first = False
                else:
                    den.possible_duty.append(workers[key].letter)
        calendar[day] = den

    return calendar

def timespan_ideal_values(kalendar_source,workers_sources, months): #counts some ideal values like average weekdays and workdays and distributes among workers based on their preference
    #which can be fixed or average
    workers = workers_sources
    kalendar = kalendar_source
    minus_weekend = 0
    weekend_workers = 0
    minus_workday = 0
    workday_workers = 0
    total_workday = 0
    total_weekend = 0
    avg_index = 0

    for key in workers:
        if workers[key].limit_workday != "X":
            workers[key].limit_workday = int(workers[key].limit_workday) * months
            minus_workday += float(workers[key].limit_workday)
        else:
            workday_workers += 1 #up count the number of people who dont have fixed workday counts
        if workers[key].limit_weekend != "X":
            workers[key].limit_weekend = int(workers[key].limit_weekend) * months
            minus_weekend += float(workers[key].limit_weekend)
        else:
            weekend_workers += 1 #up count the number of people who dont have fixed weekday counts

    for day in kalendar:
        avg_index += kalendar[day].index
        if kalendar[day].index > 1.29:
            total_weekend += 1
        else:
            total_workday += 1

    ideal_workday = 0
    ideal_workday = total_workday - minus_workday
    ideal_workday = ideal_workday / workday_workers
    ideal_weekend = 0
    ideal_weekend = total_weekend - minus_weekend
    ideal_weekend = ideal_weekend / weekend_workers

    avg_index = avg_index / len(kalendar)

    return (ideal_workday, ideal_weekend, avg_index)

def generate_random_Sequence(abeceda, kalendar, firstday): #generates random sequence of workers for given time span. letters only.
    #why dont i use just first letter for example? because Skach and Skaryd would look the same in the sequence for human eye
    random_Sequence = Sequence(0,"")
    
    i = 0
    while i < len(kalendar):
        current_date = firstday + timedelta(days = i)
        current_date = current_date.strftime('%Y-%m-%d')

        random_Sequence.workers += (random.choice(kalendar[current_date].possible_duty))
        i += 1

    return random_Sequence

def generate_first_population(size, abeceda, kalendar, firstday): #generate the first test population with random sequences up to limits in constants
    first_Population = Population(0,[])
    i = 0
    while i < (size):
        first_Population.sequences.append(generate_random_Sequence(abeceda, kalendar, firstday))
        i = i + 1

    first_Population.maxfitness = 0
    first_Population.minfitness = 40000

    return first_Population

def update_workers_with_ideal_values(workers,ideal_workday,ideal_weekend): #update all workers from X for average to a certain float number * employment rate
    for key in workers:
        if workers[key].limit_workday == "X":
           workers[key].limit_workday = ideal_workday * float(workers[key].employment)
        if workers[key].limit_weekend == "X":
           workers[key].limit_weekend = ideal_weekend * float(workers[key].employment)
    
    return workers

def count_population_fitness(Population, currentAbeceda, workers, kalendar, firstday, ideal_fridays):
    #count population fitness
    for key in Population.sequences:
        key.fitness = entity_fitness(workers,key,kalendar,firstday,ideal_fridays)

    for key in Population.sequences:
        if key.fitness > Population.maxfitness:
            Population.maxfitness = key.fitness
        if key.fitness < Population.minfitness:
            Population.minfitness = key.fitness

    return [Population.maxfitness,Population.minfitness]

def get_ideal_friday(workers, kalendar, firstday): #count ideal friday count per worker, people hate fridays
    fridays = 0
    for key in kalendar:
        if kalendar[key].index == 1.25:
            fridays += 1

    result = fridays / len(workers)

    return result

def entity_fitness(workers,Sequence,kalendar,firstday,ideal_fridays): #the ALPHA AND OMEGA OF THE SCRIPT, HERE MAGIC IS SUPPOSED TO HAPPEN
    total_fitness = 0

    #WE scan each worker
    for key in workers:
        #---------------------------------------------------
        currentWorker = Worker(0,0,0,0,0,0,0,0,0,0,[],[])
        currentWorker = workers[key]
        limit_workday = currentWorker.limit_workday
        limit_weekend = currentWorker.limit_weekend
        duties = []
        duties_p = []
        duties_friday = []
        duties_weekend = []
        weekend = -1
        workdays = -1
        fridays = -1
        penalty_count = 0
        penalty_interval = 0
        penalty_critical = 0
        penalty_weekend = 0
        penalty_fridays = 0
        penalty = 0

        
        #in this cycle it is supposed to add indexes into workday or weekendday arrays where the worker has duty assigned in this sequence 
        #we use this data to look for weekday numbers, weekendday numbers and intervals between the duties
        yy = 0
        while yy < len (Sequence.workers):
            current_date = firstday + timedelta(days = yy)
            current_date = current_date.strftime('%Y-%m-%d')
            if Sequence.workers[yy] == currentWorker.letter:
                if kalendar[current_date].index == 1.125 : #Mo Tu We
                    duties_p.append(yy)
                if kalendar[current_date].index == 1.01 : #Th
                    duties_p.append(yy)
                if kalendar[current_date].index == 1.25 : #Friday
                    duties_friday.append(yy)
                if kalendar[current_date].index == 1.3 : #Sunday
                    duties_weekend.append(yy)
                if kalendar[current_date].index == 1.37 : #Saturday
                    duties_weekend.append(yy)
            yy +=1

        if int(limit_weekend) <= len(duties_weekend) <= int(limit_weekend)+1: # if number of actual weekendday duties is larger then average or given by limit it creates a penalty
            pass
        else:
            penalty_count = Penalty_count #Penalty
            #print ("Penalty for weekend duties count non cumulative", Penalty_count)
            
        duties_pv = duties_friday + duties_weekend #we organize friday and sat and SUN duties by position in time sequence.
        duties_pv = list(dict.fromkeys(duties_pv))
        duties_pv.sort(key=int)

        duties_p = duties_p + duties_friday #we organize Mo Tu Wed Th and Fri duties the same way as above
        duties_p = list(dict.fromkeys(duties_p))
        duties_p.sort(key=int)

        duties = duties_p + duties_pv #we pull up all kind of duties into one big array 
        duties = list(dict.fromkeys(duties))
        duties.sort(key=int)

        if int(limit_workday) <= len(duties_p) <= int(limit_workday)+1: #if number of actual workday duties is larger then average or giben by limit it creates a penalty
            pass
        else:
            penalty_count = Penalty_count #Penalty
            #print ("Penalty for count of workday duties, non cumulative", Penalty_count)

        if int(limit_workday+limit_weekend) <= len(duties) <= int(limit_workday+limit_weekend)+1: #we penalize the total duty count too
            pass
        else:
            penalty_count += Penalty_count #Penalty
            #print ("Penalty for total number of duties.", Penalty_count)

        fridays = len(duties_friday)
        if int(ideal_fridays) <= fridays <=  int(ideal_fridays)+1: #we penalize if someone has more then ideal fridays
            pass
        else:
            penalty_fridays = Penalty_fridays #POSTIH
            #print ("Penalty for fridays", Penalty_fridays)

        xx = 0
        while xx < len(duties_pv): #we check if the array with fridays and weekends has any position closer then 10 which would mean a Fr Fr or Fr Sat or Fr Sun combination which we penalize
            if xx!=0:
                if duties_pv[xx]-duties_pv[xx-1]<10:
                    penalty_weekend = Penalty_weekend #POSTIH\
                    #print ("Penalty for interval weekend weekend", Penalty_weekend)
            xx += 1
        
        xx = 0
        while xx < len(duties):
            if xx!=0:
                if duties[xx]-duties[xx-1]<(int(currentWorker.min_interval)+1):  #+1? we search for days where the worker is supposed to work two days in a row which is forbidden
                    if duties[xx]-duties[xx-1] == 1:
                        penalty_critical = Penalty_critical #This should mean that the guy has two duties after each other
                    else:
                        penalty_interval = Penalty_interval #INTERVAL
                    #print ("Penalty for interval noncumulative", Penalty_interval)
            xx += 1

        penalty = penalty_count + penalty_fridays + penalty_weekend + penalty_interval + penalty_critical  #add all penalties into one number.
        fitness = 0
        fitness = Theoretical_fitness - penalty #we substract the penalties from maximum number of possible penalties and get a fitness value.
        total_fitness += fitness

    return total_fitness

def fin_entity_fitness(workers,Sequence,kalendar,firstday,ideal_fridays): #THIS IS basically a CLONE of entity_fitness function above, a product of lazyness
    #this entire function could be removed and some activators implemented into entity_fitness to enable different penalty values for this final pass.
    total_fitness = 0
    Penalty_interval = 300 #300
    Penalty_weekend = 150 #150
    Penalty_fridays = 50 #50
    Penalty_count = 1000 #1000
    Penalty_critical = 1500
    Theoretical_fitness = Penalty_interval + Penalty_critical + Penalty_weekend + Penalty_fridays + Penalty_count #funguje slusne s all 300

    for key in workers:
        #---------------------------------------------------
        currentWorker = Worker(0,0,0,0,0,0,0,0,0,0,[],[])
        currentWorker = workers[key]
        limit_workday = currentWorker.limit_workday
        limit_weekend = currentWorker.limit_weekend
        duties = []
        duties_p = []
        duties_friday = []
        duties_weekend = []
        weekend = -1
        workdays = -1
        fridays = -1
        penalty_count = 0
        penalty_interval = 0
        penalty_weekend = 0
        penalty_fridays = 0
        penalty = 0

        #print (currentWorker.letter, Sequence.workers)

        yy = 0
        while yy < len (Sequence.workers):
            current_date = firstday + timedelta(days = yy)
            current_date = current_date.strftime('%Y-%m-%d')
            if Sequence.workers[yy] == currentWorker.letter:
                if kalendar[current_date].index == 1.125 : #Po Ut St
                    duties_p.append(yy)
                if kalendar[current_date].index == 1.01 : #Ctvrtek
                    duties_p.append(yy)
                if kalendar[current_date].index == 1.25 : #friday
                    duties_friday.append(yy)
                if kalendar[current_date].index == 1.3 : #nedele
                    duties_weekend.append(yy)
                if kalendar[current_date].index == 1.37 : #sobota
                    duties_weekend.append(yy)
            yy +=1

        if int(limit_weekend) <= len(duties_weekend) <= int(limit_weekend)+1: #pocet weekendu musi byt vetsi nebo rovno limit_weekend a mensi nebo rovno limit_weekend +1            
            pass
        else:
            print ("Penalty for count of sluzeb",key) #This is just printed in the last part of the program to inform about which penalties were given, in the endstage, there should be like 2-3 penalties max
            penalty_count = Penalty_count #POSTIH
            #print ("Penalty for count of sluzeb weekend nekumulativni", Penalty_count)
            
        duties_pv = duties_friday + duties_weekend #
        duties_pv = list(dict.fromkeys(duties_pv))
        duties_pv.sort(key=int)

        duties_p = duties_p + duties_friday
        duties_p = list(dict.fromkeys(duties_p))
        duties_p.sort(key=int)

        duties = duties_p + duties_pv #
        duties = list(dict.fromkeys(duties))
        duties.sort(key=int)

        if int(limit_workday) <= len(duties_p) <= int(limit_workday)+1:
            pass
        else:
            print ("Penalty for count of workday",key)
            penalty_count = Penalty_count #POSTIH
            #print ("Penalty for count of sluzeb workday nekumulativni", Penalty_count)

        if int(limit_workday+limit_weekend) <= len(duties) <= int(limit_workday+limit_weekend)+1:
            pass
        else:
            print ("Penalty for count of weekend",key)
            penalty_count += Penalty_count #POSTIH
            #print ("Penalty for count of sluzeb total", Penalty_count)

        fridays = len(duties_friday)
        if int(ideal_fridays) <= fridays <=  int(ideal_fridays)+1:
            pass
        else:
            print ("Penalty for count of fridays",key)
            penalty_fridays = Penalty_fridays #POSTIH
            #print ("Postih za fridays", Penalty_fridays)

        xx = 0
        while xx < len(duties_pv):
            if xx!=0:
                if duties_pv[xx]-duties_pv[xx-1]<10:
                    print ("Penalty for weekend interval",key)
                    penalty_weekend = Penalty_weekend #POSTIH\
                    #print ("Postih za interval weekend weekend", Penalty_weekend)
            xx += 1
        
        xx = 0
        while xx < len(duties):
            if xx!=0:
                if duties[xx]-duties[xx-1]<(int(currentWorker.min_interval)+1):  #+1? Ob jeden
                    if duties[xx]-duties[xx-1]== 1:
                        penalty_critical = Penalty_critical #POZOR???
                        print ("Critical penalty",key)
                    else:
                        penalty_interval = Penalty_interval #INTERVAL
                    #print ("Postih za interval nekumulativni", Penalty_interval)
            xx += 1

        penalty = penalty_count + penalty_fridays + penalty_weekend + penalty_interval
        #print ("Pokuta",penalty)
        fitness = 0
        fitness = Theoretical_fitness - penalty #za ucast je 2, ale asi by to chtelo proporcne k poctu lidi?
        total_fitness += fitness

        #print("Fit", fitness, "/ total",total_fitness)
        #input("Press Enter to continue...")

    return total_fitness

def create_selection_pool(currentAbeceda, PopulationS, kalendar, first_day, maxfitness, minfitness): #we create a selection pool from the better specimens based on fitness
    hat = Population(0,0,[])
    ratio = (maxfitness +1 - minfitness)/100
    total_fitness = 0
    highest_fitness = 0
    entity_count = len(PopulationS.sequences)
    
    #we remove below average specimens from the population first
    for key in PopulationS.sequences:
        total_fitness += key.fitness
        if key.fitness > highest_fitness:
            highest_fitness = key.fitness
    average_fitness = total_fitness / entity_count
    for key in PopulationS.sequences:
        if key.fitness < average_fitness:
            PopulationS.sequences.remove(key)
    #we breed the remaining specimens to fill the hat, a hat which is quite larger then population with hundreds of specimens, the best can have thousands of copies, the worst only several
    #we do this to make the random chance more real later.

    x = 0
    specimen = Sequence(0,"")
    for key in PopulationS.sequences:
        if key.fitness == maxfitness:
            specimen = key
    
    for key in PopulationS.sequences:
        i = 0
        while i < ((key.fitness +1 - minfitness)/ratio):
            hat.sequences.append(key)
            i += 1

    return hat, specimen #we return the pool / hat and the best specimen in it

def mutate(currentAbeceda, mutation_chance, entity, kalendar, firstday): #we perform mutation based on mutation rate constant, we switch one letter with another from the list of available
    i = 0

    new_entity = ""
    while i < len(entity):
        current_date = firstday + timedelta(days = i)
        current_date = current_date.strftime('%Y-%m-%d')
        if random.randint(0, 100) < mutation_chance:
            test = random.choice(kalendar[current_date].possible_duty)
            new_entity += test
        else:
            new_entity += entity[i]
        i += 1

    return new_entity

def generate_population(hat, population_size, mutation, kalendar, first_day, elite_specimen): #we create a new population from the breeding pool.
    new_population = Population(0,0,[])

    x = 0
    while x < population_size/ElitePercentage: #first we introduce a certain number of elite speciments
        new_population.sequences.append(elite_specimen)
        x += 1

    while x < (population_size/2-population_size/ElitePercentage): #then we fill the rest with specimens that we crossover
        parentAR = Sequence(0,"")
        parentBR = Sequence(0,"")
        parentAR = random.choice(hat.sequences)
        parentBR = random.choice(hat.sequences)

        #crossover
        parentA = parentAR.workers
        parentB = parentBR.workers

        y = 1
        childA = parentA[:1]
        childB = parentB[:1]

        while y < len(parentA):
            rand_number = random.randint (0,1) #we basically put along two specimens, and switch letters if the chance is right = crossover rate constant
            if rand_number == 0:
                childA = childA[:y] + parentA[y:]
                childB = childB[:y] + parentB[y:]
            if rand_number == 1:
                childA = childA[:y] + parentB[y:]
                childB = childB[:y] + parentA[y:]
            y += 1

        childAR = Sequence(0,"")
        childBR = Sequence(0,"")

        childAR.workers = childA
        childBR.workers = childB

        childAR.workers = mutate(abeceda,mutation,childAR.workers,kalendar, first_day)
        childBR.workers = mutate(abeceda,mutation,childBR.workers,kalendar, first_day)

        new_population.sequences.append(childAR) #we inject two children per two parents into the population
        new_population.sequences.append(childBR)
        x += 1

    return new_population

def save_results(kalendar): #save the final results into a text file
    with open("results.txt", "w") as f:
        for day in kalendar:
            #content = day  + " " + kalendar[day].worker + "\n"
            f.write (kalendar[day].worker + "\n")
    return True

#CORE 
Best_specimen_af = Sequence(0,"")
Elite_specimen_af = Sequence(0,"")
Best_specimen_eu = Sequence(0,"")
Elite_specimen_eu = Sequence(0,"")
Best_specimen_au = Sequence(0,"")
Elite_specimen_au = Sequence(0,"")
Best_specimen_am = Sequence(0,"")
Elite_specimen_am = Sequence(0,"")
Best_specimen_an = Sequence(0,"")
Elite_specimen_an = Sequence(0,"")
Best_specimen = Sequence(0,"")

workers_sources, abeceda = load_worker_sources(WorkersFilename) #we load up the workers
first_day, last_day = calendar_interval_get() #we find out the first and last day of the time span
kalendar_source, months = calendar_genesis(first_day,last_day) #we made a calendar
kalendar_source = calendar_availability(kalendar_source,workers_sources) #we fill the calendar with workers who want to work, yey
ideal_fridays = get_ideal_friday(workers_sources,kalendar_source,first_day) #we count ideal fridays
ideal_workday, ideal_weekend, ideal_index = timespan_ideal_values(kalendar_source,workers_sources,months) #we count some more ideal values
workers_sources = update_workers_with_ideal_values(workers_sources,ideal_workday,ideal_weekend) #we update some data in workers with the new ideal values

#This is such a bad approach, i should have put the populations into an ARRAY, and add the Best and Elite specimens as their variable, is something to do in future
#But 5 pop islands works nice. If i have just one population the sequences are ALL TOO SImilar. This way i have DIVERSITY.
first_Population_africa = generate_first_population(PopulationSize, abeceda, kalendar_source, first_day) #we failed with single population results, so we made 5, 
first_Population_eurasia = generate_first_population(PopulationSize, abeceda, kalendar_source, first_day) 
first_Population_australia = generate_first_population(PopulationSize, abeceda, kalendar_source, first_day)
first_Population_america = generate_first_population(PopulationSize, abeceda, kalendar_source, first_day) 
first_Population_antarktis = generate_first_population(PopulationSize, abeceda, kalendar_source, first_day)

maxfitness_af, minfitness_af = count_population_fitness(first_Population_africa,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays) #count fitness in Population
print ("Africa generated.")
maxfitness_eu, minfitness_eu = count_population_fitness(first_Population_eurasia,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays) 
print ("Eurasia generated.")
maxfitness_au, minfitness_au = count_population_fitness(first_Population_australia,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays) 
print ("Australia generated.")
maxfitness_am, minfitness_am = count_population_fitness(first_Population_america,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays) 
print ("America generated.")
maxfitness_an, minfitness_an = count_population_fitness(first_Population_antarktis,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays) 
print ("Antarktis generated.")
hat_selekce_af, Best_specimen_af = create_selection_pool(abeceda, first_Population_africa, kalendar_source, first_day, maxfitness_af, minfitness_af) #selection pool, breeding
hat_selekce_eu, Best_specimen_eu = create_selection_pool(abeceda, first_Population_eurasia, kalendar_source, first_day, maxfitness_eu, minfitness_eu) 
hat_selekce_au, Best_specimen_au = create_selection_pool(abeceda, first_Population_australia, kalendar_source, first_day, maxfitness_au, minfitness_au) 
hat_selekce_am, Best_specimen_am = create_selection_pool(abeceda, first_Population_america, kalendar_source, first_day, maxfitness_am, minfitness_am) 
hat_selekce_an, Best_specimen_an = create_selection_pool(abeceda, first_Population_antarktis, kalendar_source, first_day, maxfitness_an, minfitness_an)

Population_af = generate_population(hat_selekce_af,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_af) #new population culled from the selection pool
Population_eu = generate_population(hat_selekce_eu,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_eu) 
Population_au = generate_population(hat_selekce_au,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_au) 
Population_am = generate_population(hat_selekce_am,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_am) 
Population_an = generate_population(hat_selekce_an,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_an) 
#cyklus mutaci hruby
u = 0
print ("Beginning phase 1.") #there should have been a phase 2 with different mutation rate one day

while (u < Cycles) and (Best_specimen.fitness != Theoretical_fitness*len(workers_sources)): 
    print ("Done from ", u/(Cycles/100)," procent.", end = "\r")

    maxfitness_af, minfitness_af = count_population_fitness(Population_af,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays) #count fitness Population
    maxfitness_eu, minfitness_eu = count_population_fitness(Population_eu,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays)
    maxfitness_au, minfitness_au = count_population_fitness(Population_au,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays)
    maxfitness_am, minfitness_am = count_population_fitness(Population_am,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays)
    maxfitness_an, minfitness_an = count_population_fitness(Population_an,abeceda,workers_sources,kalendar_source,first_day,ideal_fridays)

    hat_selekce_af, Elite_specimen_af = create_selection_pool(abeceda, Population_af, kalendar_source, first_day, maxfitness_af, minfitness_af) #selection
    hat_selekce_eu, Elite_specimen_eu = create_selection_pool(abeceda, Population_eu, kalendar_source, first_day, maxfitness_eu, minfitness_eu) 
    hat_selekce_au, Elite_specimen_au = create_selection_pool(abeceda, Population_au, kalendar_source, first_day, maxfitness_au, minfitness_au)
    hat_selekce_am, Elite_specimen_am = create_selection_pool(abeceda, Population_am, kalendar_source, first_day, maxfitness_am, minfitness_am)
    hat_selekce_an, Elite_specimen_an = create_selection_pool(abeceda, Population_an, kalendar_source, first_day, maxfitness_an, minfitness_an)
    
    if Elite_specimen_af.fitness >= Best_specimen_af.fitness: #find actual best specimens and all time best specimens
        Best_specimen_af = Elite_specimen_af
        if Best_specimen_af.fitness > Best_specimen.fitness:
            Best_specimen = Best_specimen_af
    if Elite_specimen_eu.fitness >= Best_specimen_eu.fitness:
        Best_specimen_eu = Elite_specimen_eu
        if Best_specimen_eu.fitness > Best_specimen.fitness:
            Best_specimen = Best_specimen_eu
    if Elite_specimen_au.fitness >= Best_specimen_au.fitness:
        Best_specimen_au = Elite_specimen_au
        if Best_specimen_au.fitness > Best_specimen.fitness:
            Best_specimen = Best_specimen_au
    if Elite_specimen_am.fitness >= Best_specimen_am.fitness:
        Best_specimen_am = Elite_specimen_am
        if Best_specimen_am.fitness > Best_specimen.fitness:
            Best_specimen = Best_specimen_am
    if Elite_specimen_an.fitness >= Best_specimen_an.fitness:
        Best_specimen_an = Elite_specimen_an
        if Best_specimen_an.fitness > Best_specimen.fitness:
            Best_specimen = Best_specimen_an

    print ("Best in Africe    ", Best_specimen_af.fitness, " from ", Theoretical_fitness*len(workers_sources), Best_specimen_af.workers)
    print ("Best in Eurasii   ", Best_specimen_eu.fitness, " from ", Theoretical_fitness*len(workers_sources), Best_specimen_eu.workers)
    print ("Best in Australii ", Best_specimen_au.fitness, " from ", Theoretical_fitness*len(workers_sources), Best_specimen_au.workers)
    print ("Best in Americe   ", Best_specimen_am.fitness, " from ", Theoretical_fitness*len(workers_sources), Best_specimen_am.workers)
    print ("Best in Antarktis ", Best_specimen_an.fitness, " from ", Theoretical_fitness*len(workers_sources), Best_specimen_an.workers)
    print ("Best globaly      ", Best_specimen.fitness, " from ", Theoretical_fitness*len(workers_sources), Best_specimen.workers)

    Population_af = generate_population(hat_selekce_af,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_af) #new populations 
    Population_eu = generate_population(hat_selekce_eu,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_eu) 
    Population_au = generate_population(hat_selekce_au,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_au) 
    Population_am = generate_population(hat_selekce_am,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_am) 
    Population_an = generate_population(hat_selekce_an,PopulationSize,MutationRate,kalendar_source, first_day, Best_specimen_an) 
    
    u += 1

print ("")

rating_af = fin_entity_fitness(workers_sources, Best_specimen_af, kalendar_source, first_day, ideal_fridays ) #count the fitness using different values for penalties once
rating_eu = fin_entity_fitness(workers_sources, Best_specimen_eu, kalendar_source, first_day, ideal_fridays )
rating_au = fin_entity_fitness(workers_sources, Best_specimen_au, kalendar_source, first_day, ideal_fridays )
rating_am = fin_entity_fitness(workers_sources, Best_specimen_am, kalendar_source, first_day, ideal_fridays )
rating_an = fin_entity_fitness(workers_sources, Best_specimen_an, kalendar_source, first_day, ideal_fridays )

results = {"af":rating_af,"eu":rating_eu,"au":rating_au,"am":rating_am,"an":rating_an} #find the best one based on the different values for penalties
max = max(results, key=results.get)

if max == "af":
    Best_specimen = Best_specimen_af
if max == "eu":
    Best_specimen = Best_specimen_eu
if max == "au":
    Best_specimen = Best_specimen_au
if max == "am":
    Best_specimen = Best_specimen_am
if max == "an":
    Best_specimen = Best_specimen_an

print ("Final.", Best_specimen.workers)
test = fin_entity_fitness(workers_sources, Best_specimen, kalendar_source, first_day, ideal_fridays)

# Generate the final calendar based on the very best specimen
zz = 0
while zz < len(Best_specimen.workers):
    current_date = first_day + timedelta(days = zz)
    current_date = current_date.strftime('%Y-%m-%d')

    for key in workers_sources:
        if workers_sources[key].letter == Best_specimen.workers[zz]:
            kalendar_source[current_date].worker = key
    
    zz += 1
    

# Print to screen
print ("          ", end = " ")
for key in workers_sources:
    print (key[:3], end=" ")
print("")
for day in kalendar_source:
    print (day, end= " ")
    for key in workers_sources:
        if key == kalendar_source[day].worker:
            print (" X ", end = " ")
            if workers_sources[key].letter not in kalendar_source[day].possible_duty:
                print ("Hard limit error")
        else:
            print ("   ", end = " ")
    print (" ")

#Notes for the human which can not be implemented via a strict YES or NO setting
print("Kocmanova desires v Zari jen dve duties")
print("Rambo nedesires v Cervenci a Srpnu duties")
print("Skach desires co nejvic sluzeb mezi 2 a 12 srpnem")

save_results(kalendar_source)