class PID:
    def __init__(self, proportional_const, integral_const, differential_const, set_point = None, positive_wind_up = 10, negative_wind_up = -10, dt= 0.01):
        """A reusable class for PID control. 
        Takes P, I, D constants, set_point and history time as args."""
        self.p_const = proportional_const
        self.i_const = integral_const
        self.d_const = differential_const
        self.set_point = set_point
        #self.error_history = deque((), 100)
        self.previous_error = 0
        self.positive_wind_up = positive_wind_up
        self.negative_wind_up = negative_wind_up
        self.integral_sum = 0
        self.dt = dt
    def update(self, current_value, target=None):
        #Returns the current sum of P, I, D terms
        if target:
            error = target - current_value
        else:
            error = self.set_point - current_value
        self.integral_sum=max(self.negative_wind_up, min(error+self.integral_sum, self.positive_wind_up))
        #self.error_history.append(error)
        
        p_term = error*self.p_const
        #print('p term: ', p_term)
        i_term = self.integral_sum*self.i_const*self.dt
        #print('i term: ', i_term)
        d_term = (error - self.previous_error)*self.d_const/self.dt
        #print('d term: ', d_term)
        self.previous_error = error
       
        return p_term + i_term + d_term

if __name__ == '__main__':
    import utime
    print("Running sample simulations")
    dt = 0.1

    pid = PID(proportional_const=0.7, integral_const=0.02, differential_const=0.001, set_point=90.0, positive_wind_up=5, negative_wind_up=-5, dt = dt)

    temp = 25
    time = 0
    scale_ratio = 1.0
    while True:
        print(f'Current temperature: {temp} at time {time}')
        pid_sum =pid.update(temp)
        print('Current P+I+D sum: ', pid_sum)
        temp += scale_ratio*pid_sum
        utime.sleep(dt)
        time+=1

