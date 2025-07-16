import json

class profile_handler:
    def __init__(self):
        
        self.profile_name = ''
        self.time_step_ms = 0
        self.profile_stages = []
        self.temperature = 0
        self.duration = 0

    def load_profile(self, profile_name):
        f = open(f'/brew_profiles/{profile_name}.json')
        profile = json.load(f)

        self.profile_name = profile['profile_name']
        self.time_step_ms = profile['time_step_ms']
        self.profile_stages = profile['profile_points']
        self.temperature = profile['target_temp_c']
        self.duration = profile['total_duration_ms']
        
    def get_target_at_time(self, current_time_ms):
        if current_time_ms == 0:
            if self.profile_stages[0][0] == 0:
                return self.profile_stages[0][2]
            else:
                return None 

        time_at_start = 0
        
        for profile_stage in self.profile_stages:
           time_at_end = time_at_start + profile_stage[0]
           
           if current_time_ms > time_at_start and current_time_ms <= time_at_end:
               interpolation = profile_stage[1]

               if interpolation == 'hold':
                   return profile_stage[2]
               elif interpolation == 'linear':
                   return self._calculate_linear(
                       initial_pressure=profile_stage[2], 
                       final_pressure=profile_stage[3], 
                       duration=profile_stage[0], 
                       current_time_ms=current_time_ms, 
                       time_elapsed=time_at_start
                   )
           time_at_start = time_at_end

        last_stage = self.profile_stages[-1]
        if last_stage[1] == 'hold':
            return last_stage[2]
        else:
            return last_stage[3]

    def _calculate_linear(self, initial_pressure, final_pressure, duration, current_time_ms, time_elapsed):
        # Prevent division by zero if a linear ramp has zero duration
        if duration == 0:
            return initial_pressure
            
        slope = (final_pressure - initial_pressure) / duration
        x = current_time_ms - time_elapsed
        pressure_value = slope * x + initial_pressure
        return pressure_value
    
if __name__ == '__main__':
    import utime
    p_h = profile_handler()
    p_h.load_profile('standard9')
    for t in range(0, p_h.duration, 100):
        utime.sleep_ms(100)
        print(f'Current pressure: {p_h.get_target_at_time(t)} at time: {t}')
