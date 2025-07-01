import json


class profile_handler:
    def __init__(self, profile):
        self.profile_name = profile['profile_name']
        self.time_step_ms = profile['time_step_ms']
        self.profile_stages = profile['profile_points']
        self.temperature = profile['target_temp_c']
        
    def get_target_at_time(self, current_time_ms):
        current_stage = []
        time_elapsed = 0
        initial_pressure = 0

        for profile_stage in self.profile_stages:
            if current_time_ms <= profile_stage[0] + time_elapsed:
                current_stage = profile_stage
                break
            time_elapsed+=profile_stage[0]

        duration = current_stage[0]
        pressure = current_stage[1]
        interpolation = current_stage[2]

        if interpolation == 'hold':
            #result = self._calculate_hold(pressure=pressure, duration=duration, current_time_ms=current_time_ms)
            initial_pressure = pressure
            return pressure
        elif interpolation == 'linear':
            initial_pressure = self.get_target_at_time(time_elapsed)
            result = self._calculate_linear(initial_pressure=initial_pressure, final_pressure=pressure, duration=duration, 
                                            current_time_ms=current_time_ms, time_elapsed = time_elapsed)
            return result

    # def _calculate_hold(self, pressure, duration, current_time_ms):
    #     return 

    def _calculate_linear(self, initial_pressure, final_pressure, duration, current_time_ms, time_elapsed):
        slope = (final_pressure-initial_pressure)/duration
        x = current_time_ms - time_elapsed
        pressure_value = slope*x + initial_pressure
        return pressure_value
    
if __name__ == '__main__':
    import utime
    f = open('/brew_profiles/standard9.json')
    data = json.load(f)
    print(data)
    p_h = profile_handler(data)
    for t in range(0, data['total_duration_ms'], 100):
        utime.sleep_ms(100)
        print(f'Current pressure: {p_h.get_target_at_time(t)} at time: {t}')
