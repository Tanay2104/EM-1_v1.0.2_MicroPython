from pid import PID
import utime

class BrewController:
    def __init__(self, motor, pressure_sensor, temp_sensor, pid_parameters, profile_handler):
        self.motor = motor
        self.pressure_sensor = pressure_sensor
        self.temp_sensor = temp_sensor
        self.pid = PID(*pid_parameters)
        self.profile_handler = profile_handler
        self.shot_log = []

    def do_brew_cycle(self, time):
        target_pressure = self.profile_handler.get_target_at_time(time)
        current_pressure = self.pressure_sensor.pressure
        current_temp = self.temp_sensor.temperature

        pid_output = self.pid.update(current_value=current_pressure, target=target_pressure)
        motor_speed = self.motor.convert_pid_to_speed(pid_output)
        self.motor.set_speed(motor_speed)

        self.shot_log.append((time, target_pressure,current_pressure, current_temp))

    def execute_brew(self):

        time_step_ms = self.profile_handler.time_step_ms
        duration_ms = self.profile_handler.duration

        start_time = utime.ticks_ms()

        for current_loop_time_ms in range(0, duration_ms, time_step_ms):
            
            next_tick = start_time + current_loop_time_ms + time_step_ms

            self.do_brew_cycle(current_loop_time_ms)
            
            while utime.ticks_ms() < next_tick:
                self.motor.stop()
        
    def get_shot_log(self):
        return self.shot_log







        
