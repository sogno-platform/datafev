
import datetime as dt
from src.datafev.protocols.scenariogeneration import sceneration
from src.datafev.protocols.scenariogeneration import utils

def main():
    """
    Example script for the usage of dependent times scenario generator.

    """
    
    times_dict, arr_dep_times_dict, arr_soc_dict, dep_soc_dict, ev_dict = \
        utils.excel_to_sceneration_input_dependent_times(file_path='input_generator.xlsx')

    ev_df = sceneration.generate_fleet_data_dependent_times(arr_soc_dict=arr_soc_dict, dep_soc_dict=dep_soc_dict, ev_dict=ev_dict,
                                 number_of_evs=5, startdate=dt.date(2021, 6, 1), enddate=dt.date(2021, 6, 3),
                                 timedelta_in_min=15, diff_arr_dep_in_min=0, times_dict=times_dict,
                                 arr_dep_times_dict=arr_dep_times_dict)
    
    utils.visualize_statistical_time_generation('', ev_df, timedelta_in_min=15)
    
    # Unlocalize datetimes, as Excel does not support datetimes with timezones
    ev_df['ArrivalTime'] = ev_df['ArrivalTime'].dt.tz_localize(None)
    ev_df['DepartureTime'] = ev_df['DepartureTime'].dt.tz_localize(None)
    ev_df.to_excel('output_generator_dependent_times.xlsx')
    
    utils.output_to_sim_input(ev_df, 'input_simulator_dependent_times.xlsx')
    
if __name__ == "__main__":
    main()