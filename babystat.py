__version__ = '0.1.0'

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as sc


class Child:

    def __init__(self, gender, birthday, name='child'):
        """
        Parameters
        ----------
        gender : str
            The gender of the animal. Either 'male' or 'female'. Controls which
            WHO data is downloaded
        birthday : str
            The birthday of the child in the format YYYY-mm-dd
        name : str, optional
            The number of legs the animal (default is 'child')

        Raises
        ------
        ValueError
            If gender is neither 'male' nor 'female.
        """
        self._gender = gender
        self._birthday = birthday
        self._name = name

        print(f'retrieving WHO child growth data for {gender}s ...')

        # Retrieve WHO child growth data from WHO web page
        if gender == 'male':

            url = 'http://www.who.int/childgrowth/standards/wfa_boys_z_exp.txt'
            self._growth_data = pd.read_csv(url, sep='\t')
            print('done.')

        elif gender == 'female':

            url = 'http://www.who.int/childgrowth/standards/wfa_girls_z_exp.txt'
            self._growth_data = pd.read_csv(url, sep='\t')
            print('done.')

        else:
            raise ValueError('child must be \'male\' or \'female\'')

    def __str__(self):
        """
        Operator overloaded string representation. Prints

            Name: <name>
            Date of birth: <YYYY-mm-dd>
            Gender: <gender>
        """
        return f'Name: {self._name}\n' \
               f'Date of Birth: {self._birthday}\n' \
               f'Gender: {self._gender}'

    @staticmethod
    def import_weight_data(weight_file):
        """
        Imports weight data of child from *.csv file. File needs following
        format:
            date, measured_weight
            YYYY-mm-dd, <weight_value_in_kg>
            YYYY-mm-dd, <weight_value_in_kg>
            ...

        Imported data is wrangled to calculate the following additional keys:
            - 'life_days': child age in days
            - 'measurement_days': child age in days where measurements took
                place
            - 'weight_gain': child weight difference per measurement
            - 'daily_weight_gain': child weight gain per day
            - 'weekly_weight_gain': child weight gain per week

        Parameters
        ----------
        weight_file : str
            path to file with weight data

        Returns
        ------
        weight_data : pd.DataFrame
            pandas dataframe containing weight data.
        """
        # Load child data and parse dates to datestring
        weight_data = pd.read_csv(weight_file,
                                  header=0,
                                  names=['date', 'measured_weight'],
                                  parse_dates=['date'],
                                  date_parser=lambda date: pd.to_datetime(
                                      date, format='%Y-%m-%d'))

        # Construct elapsed days vector and add to dataframe
        weight_data['life_days'] = weight_data['date'] - weight_data['date'][0]

        # Find life_days where child weight was measured
        weight_data['measurement_days'] = [weight_data['life_days'][i].days for
                                           i in
                                           range(len(weight_data['life_days']))]

        # Construct weight gain
        weight_data['weight_gain'] = weight_data['measured_weight'].diff()

        # Calculate weight gain per unit time (per day)
        weight_data['daily_weight_gain'] = weight_data[
                                               'weight_gain'] / np.insert(
            np.diff(weight_data['measurement_days']), 0, 0) * 7

        # Construct weekly weight gain
        weekly_weight_gain = []

        for i in range(len(weight_data)):
            begin_date = weight_data.iloc[i]['life_days'] - \
                         pd.Timedelta(6, unit='d')

            end_date = weight_data.iloc[i]['life_days']
            subset = weight_data.set_index('life_days').loc[begin_date:end_date]

            if (len(subset) == 1) and (weight_data.iloc[i][
                                           'measurement_days'] -
                                       weight_data.iloc[i - 1][
                                           'measurement_days'] > 6):
                weekly_weight_gain.append(
                    weight_data.iloc[i]['daily_weight_gain'])
            else:
                weekly_weight_gain.append(sum(subset['weight_gain']))

        weight_data['weekly_weight_gain'] = weekly_weight_gain

        return weight_data

    def _fill_percentile_curves(self, weight_offset=0, **kwargs):
        """
        Plot helper sigma bands fillings of child data. Accepts **kwargs of
        matplotlib.pyplot.plot function.

        Parameters
        ----------
        weight_offset : float
            difference from child birth weight to WHO mean weight at life day
            zero.

        Returns
        ------
        weight_data : pd.DataFrame
            pandas dataframe containing weight data.
        """

        # Plot Mean and 1,2,3 sigma
        plt.plot(self._growth_data['Day'],
                 self._growth_data['SD0'] + weight_offset,
                 **kwargs)
        plt.fill_between(self._growth_data['Day'],
                         self._growth_data['SD1neg'] + weight_offset,
                         self._growth_data['SD1'] + weight_offset,
                         **kwargs, alpha=0.3)
        plt.fill_between(self._growth_data['Day'],
                         self._growth_data['SD2neg'] + weight_offset,
                         self._growth_data['SD2'] + weight_offset,
                         **kwargs, alpha=0.2)
        plt.fill_between(self._growth_data['Day'],
                         self._growth_data['SD3neg'] + weight_offset,
                         self._growth_data['SD3'] + weight_offset,
                         **kwargs, alpha=0.1)

    @staticmethod
    def _plot_child_data(child_weight_data, **kwargs):
        """
        Plot helper plotting data points with errorbars. Accepts **kwargs of
        matplotlib.pyplot.error function.

        Parameters
        ----------
        child_weight_data : pd.DataFrame
            pandas dataframe containing weight data.
        """
        plt.errorbar([child_weight_data['life_days'][i].days for i in
                      range(len(child_weight_data['life_days']))],
                     child_weight_data['measured_weight'],
                     **kwargs)

    def calculate_child_percentiles(self, child_weight_data,
                                    weight_offset=0):
        """
        Calculates percentiles for child data.

        Parameters
        ----------
        child_weight_data : pd.DataFrame
            pandas dataframe containing weight data
        weight_offset : float
            difference from child birth weight to WHO mean weight at life day
            zero

        Returns
        ------
        percentile : float
            Calculated percentile value
        """

        # Find most recent data point
        most_recent_day = child_weight_data.iloc[-1]['life_days'].days

        # Construct normal distribution mean (loc) and std deviation (scale)
        # of the WHO data for the most recent day
        loc = self._growth_data.iloc[most_recent_day]['SD0']
        scale = self._growth_data.iloc[most_recent_day]['SD0'] - \
                self._growth_data.iloc[most_recent_day]['SD1neg']

        percentile = sc.norm.cdf(child_weight_data.iloc[-1]['measured_weight'],
                                 loc + weight_offset, scale)

        return percentile

    def _percentile_plot(self, child_weight_data, x_lim, y_lim, color,
                         offset=0, name=None):
        """
        Plot helper plotting gathering all plotting information and
        forwarding it to other plot helpers.

        Parameters
        ----------
        child_weight_data : pd.DataFrame
            pandas dataframe containing weight data.
        x_lim : float
            maximum value of x axis
        y_lim : float
            maximum value of y axis
        color : matplotlib.color
            color of percentile plot
        offset : float
            difference from child birth weight to WHO mean weight at life day
            zero
        name : str
            name of child used for plotting
        """
        # Draw sigma bends
        self._fill_percentile_curves(color=color, weight_offset=offset)

        # Add child data
        self._plot_child_data(child_weight_data, color='black',
                              linestyle='none',
                              marker='o', yerr=0.25)

        # # Calculate child percentiles
        # self._calculate_child_percentiles(child_weight_data,
        # weight_offset=offset)

        # Legend, formatting, ...
        plt.legend([name,
                    r'$\pm 1\sigma$',
                    r'$\pm 2\sigma$',
                    r'$\pm 3\sigma$', '%.2f-percentile' %
                    self.calculate_child_percentiles(child_weight_data,
                                                     offset)])
        plt.xlim([1, x_lim])
        plt.ylim([2.5, y_lim])
        plt.xscale('log')
        plt.ylabel('Weight [kg]')
        plt.xlabel('Life days [d]')
        plt.grid(True, which='both', linestyle='--', linewidth=.5)

    def plot(self, child_weight_data, x_lim=400, y_lim=10,
             mode='WHO_only'):
        """
        Plotting routing doing the percentile plots.

        Parameters
        ----------
        child_weight_data : pd.DataFrame
            pandas dataframe containing weight data.
        x_lim : float
            maximum value of x axis
        y_lim : float
            maximum value of y axis
        mode : str, optional
            plotting mode. Should be one of
                - 'WHO_only' : Shows child data in WHO sigma percentile bands
                - 'child_specific' : Shows child data in sigma percentile
                bands corrected for difference from child birth weight to WHO
                mean weight at life day zero
                - 'both' : Shows both plots next to each other
        """
        # Calculate difference to WHO mean
        child_diff2mean = child_weight_data['measured_weight'][0] - \
                          self._growth_data['SD0'][0]

        if mode == 'WHO_only':

            plt.figure(figsize=[7.5, 5])
            self._percentile_plot(child_weight_data, x_lim, y_lim, color='C0',
                                  name='WHO mean')

        elif mode == 'child_specific':

            plt.figure(figsize=[7.5, 5])
            self._percentile_plot(child_weight_data, x_lim, y_lim, color='C1',
                                  name=self._name)

        elif mode == 'both':

            plt.figure(figsize=[15, 5])

            # Left side: WHO_only
            plt.subplot(1, 2, 1)

            self._percentile_plot(child_weight_data, x_lim, y_lim, color='C0',
                                  name='WHO mean')

            # Right side: child_specific
            plt.subplot(1, 2, 2)

            self._percentile_plot(child_weight_data, x_lim, y_lim, color='C1',
                                  offset=child_diff2mean, name=self._name)

        plt.show()
