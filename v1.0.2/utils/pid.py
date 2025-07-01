from collections import deque

class PID:
    def __init__(self, proportional_const, integral_const, differential_const, set_point = None, history_time = 20):
        """A reusable class for PID control. 
        Takes P, I, D constants, set_point and history time as args."""
        self.p_const = proportional_const
        self.i_const = integral_const
        self.d_const = differential_const
        self.set_point = set_point
        self.error_history = deque((), history_time)
        self.previous_error = 0
    def update(self, current_value):
        #Returns the current sum of P, I, D terms
        error = self.set_point - current_value
        self.error_history.append(error)
        
        p_term = error*self.p_const
        #print('p term: ', p_term)
        i_term = sum(self.error_history)*self.i_const
        #print('i term: ', i_term)
        d_term = (error - self.previous_error)*self.d_const
        #print('d term: ', d_term)
        self.previous_error = error
       
        return p_term + i_term + d_term

if __name__ == '__main__':
    import utime
    print("Running sample simulations")

    pid = PID(proportional_const=0.15, integral_const=0.01, differential_const=0.06, set_point=90.0, history_time=10)

    temp = 25
    time = 0
    scale_ratio = 1.0
    while True:
        print(f'Current temperature: {temp} at time {time}')
        pid_sum =pid.update(temp)
        print('Current P+I+D sum: ', pid_sum)
        temp += scale_ratio*pid_sum
        utime.sleep(0.1)
        time+=1

