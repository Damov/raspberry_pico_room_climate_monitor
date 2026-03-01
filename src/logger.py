import time

class Logger:
    """
        Logger class for single scalar time-series data. This class allows you to log scalar
        values (e.g., pressure, temperature, etc.) over time, with automatic binning of values
        into specified time intervals.

        Attributes:
        -----------
            max_bin_history: float
                Length of the history window in seconds (e.g., 3600 for 1 hour)
            bin_timespan: float
                Bin width for output in seconds (e.g., 60 for 1-minute bins)
            bin_hst_timestamp: list
                List of bin left timestamps in milliseconds
            bin_hst_values: list
                List of average values for each bin
            current_bin_start: int or None
                Start timestamp of the current bin in milliseconds, or None if no bin is active
            current_bin_value_sum: float
                Sum of values in the current bin
            current_bin_value_count: int
                Count of values in the current bin
        
        Methods:
        --------
            __init__(self, max_bin_history, bin_timespan):
                Initializes the Logger with specified history length and bin width.
            add(self, timestamp, new_value):
                Adds a new scalar value with its timestamp to the Logger, handling binning and history management.
            _remove_old(self, now):
                Removes bins that are older than the specified history length from the current time.
            bin_series(self):
                Returns the historic bin series values as a list of [dt_seconds_ago, avg_value] pairs for plotting.

        Raises:
        -------
            TypeError: If max_bin_history or bin_timespan is not a number.
            ValueError: If max_bin_history or bin_timespan is not positive.
    """
    def __init__(self, max_bin_history, bin_timespan):
        """
            Initialize the Logger.

            Arguments:
            ----------
                max_bin_history: float
                    Length of the history window in seconds (e.g., 3600 for 1 hour)
                bin_timespan: float
                    Bin width for output in seconds (e.g., 60 for 1-minute bins)
            
            Returns:
            --------
                None
                   This function initializes the Logger and does not return any value.
        """
    #-- Validate input parameters ----------------------------------------------------
        if not isinstance(max_bin_history, (int, float)):
            raise TypeError("max_bin_history must be a number")
        if not isinstance(bin_timespan, (int, float)):
            raise TypeError("bin_timespan must be a number")
        
        if max_bin_history <= 0:
            raise ValueError("max_bin_history must be positive")
        if bin_timespan <= 0:
            raise ValueError("bin_timespan must be positive")
        
    #-- Create internal attributes ---------------------------------------------------
        max_bin_history = float(max_bin_history * 1000) #.... convert total timespan of bin history to ms
        bin_timespan    = float(bin_timespan * 1000) #....... convert single bin timespan to ms

        self.max_bin_history = max_bin_history #............. save total timespan of bin history in ms
        self.bin_timespan    = bin_timespan #................ save single bin timespan in ms
    
    #-- Create longterm storage attributes -------------------------------------------
        self.bin_hst_timestamp = list() #.................... list of bin left timestamps in ms
        self.bin_hst_values    = list() #.................... list of lists of values for each bin

    #-- Create current bin accumulators ----------------------------------------------
        self.current_bin_start       = None # ............... start timestamp of the current bin in ms
        self.current_bin_value_sum   = 0.0 #................. sum of values in the current bin
        self.current_bin_value_count = 0 #................... count of values in the current bin

    #-- Return -----------------------------------------------------------------------
        return
    
    def add(self, timestamp, new_value):
        """
            Add a new scalar value and a current reference timestamp to
            the Logger.

            Arguments:
            ----------
                timestamp: int
                    The timestamp of the value in milliseconds since epoch
                    (or any consistent time unit, default can be created
                    with time.ticks_ms() ).
                new_value: float
                    The scalar value to be logged (e.g., pressure, temperature, etc.)
            
            Returns:
            --------
                None
                   This function adds a new value to the Logger and does not
                   return any value.
        """
        #now = time.ticks_ms() #...................... Current time in ms
    
    #-- If this is the first value, initialize the current bin ---------------------
        if self.current_bin_start is None:
            self.current_bin_start = timestamp

    #-- Check if we need to start a new bin ----------------------------------------
        if time.ticks_diff(timestamp, self.current_bin_start) >= self.bin_timespan:
        #-- Close the current bin --------------------------------------------------
            if self.current_bin_value_count > 0:
                avg_value = self.current_bin_value_sum \
                          / self.current_bin_value_count #.......... Calculate average value for the completed bin if count > 0
            else:
                avg_value = 0.0 #................................... Save 0 if count = 0

            self.bin_hst_values.append(avg_value) #................. Add the average value of the completed bin to the list
            self.bin_hst_timestamp.append(self.current_bin_start) #. Add the start timestamp of the completed bin to the list
        
        #-- Start a new bin --------------------------------------------------------
            self.current_bin_start       = timestamp #.............. Start timestamp of the new bin as current time
            self.current_bin_value_sum   = 0.0 #.................... Reset sum for the new bin
            self.current_bin_value_count = 0 #...................... Reset count for the new bin

    #-- Add the new value to the current bin ---------------------------------------
        self.current_bin_value_sum   += new_value
        self.current_bin_value_count += 1

    #-- Remove old bins that are outside the total timespan ------------------------
        self._remove_old(timestamp)
    
    #-- Return ---------------------------------------------------------------------
        return

    def _remove_old(self, now):
        """
            Remove bins which are older than the total time span
            (self.max_bin_history) from the current time (now).

            Arguments:
            ----------
                now: int
                    Current time in ms, default is time.ticks_ms()
            
            Returns:
            --------
                None
                   This function removes old bins from the Logger
                   and does not return any value.
        """
        cutoff = time.ticks_add(now, -int(self.max_bin_history)) #. Calculate cutoff time. Bins older than this should be removed

    #-- Iterate through data, keep only samples newer than cutoff timestamp --------
        i = 0 #.................................................. index for iterating through samples
        n = len(self.bin_hst_timestamp) #........................ total number of bins currently stored

        while i < n:
        #-- Calculate age of sample in ms using ticks_diff to handle wrap-around ---
            age_ms = time.ticks_diff(self.bin_hst_timestamp[i], cutoff)

        #-- If sample time < cutoff, ticks_diff will be negative -------------------
            if age_ms < 0:
                i += 1
            else:
                break

    #-- Remove old samples by slicing the list --------------------------------------
        if i > 0:
            self.bin_hst_timestamp = self.bin_hst_timestamp[i:] #.............. Remove old timestamps from the list
            self.bin_hst_values    = self.bin_hst_values[i:] #................. Remove old values from the list

    #-- Return ----------------------------------------------------------------------
        return
    
    def bin_series(self, convert_to_int=True):
        """
            Returns the historic bin series values.

            Arguments:
            ----------
                convert_to_int: bool
                    If True, converts the age values to integers for plotting.
            
            Returns:
            --------
                list of [dt_seconds_ago, avg_value] pairs
                    A list of pairs where dt_seconds_ago is the age of the bin center
                    in seconds (0 for now, positive  for past) and  avg_value is  the
                    average of the specified key for samples  in that particular bin.
                    Bins  are of width dt_seconds and cover the last timedelta_seconds.
        """
        now_timestamp = time.ticks_ms() #.................................. Current time in ms
    #-- Create new data structure for binned series ---------------------------------
        bin_series = list() #.............................................. List of [dt_seconds_ago, avg_value] pairs for plotting
        for i in range(len(self.bin_hst_timestamp)):
            bin_start = self.bin_hst_timestamp[i] #........................ Start timestamp of the bin in ms
            avg_value = self.bin_hst_values[i] #........................... Average value for the bin
            dt_seconds_ago = time.ticks_diff(now_timestamp, bin_start) #... Age of the bin center in ms (positive for past)
            dt_seconds_ago = dt_seconds_ago / 1000 #....................... Convert age to seconds
            bin_series.append([dt_seconds_ago, avg_value]) #............... Add the pair to the series list

    #-- Add the current bin if it has any values ------------------------------------
        if self.current_bin_value_count > 0:
            dt_seconds_ago = time.ticks_diff(now_timestamp, self.current_bin_start) #.. Age of the current bin center in ms
            dt_seconds_ago = dt_seconds_ago / 1000 #................................... Convert age to seconds
            avg_value = self.current_bin_value_sum / self.current_bin_value_count #.... Average value for the current bin
            bin_series.append([dt_seconds_ago, avg_value]) #........................... Add the current bin to the series list
    
    #-- Convert everything to integer -----------------------------------------------
        if convert_to_int:
            for i in range(len(bin_series)):
                bin_series[i][0] = int(bin_series[i][0]) #............. Convert age to integer seconds
                #bin_series[i][1] = int(bin_series[i][1]) #............. Convert average value to integer

    #-- Return the complete bin series for plotting ---------------------------------
        return bin_series
    
    def count(self):
        """
            Returns the total count of values currently stored in the Logger, including the current bin.

            Returns:
            --------
                int
                    Total count of values currently stored in the Logger, including the current bin.
        """
        return len(self.bin_series())
    
    def mean(self):
        """
            Returns the mean of the values currently stored in the Logger, including the current bin.

            Returns:
            --------
                float
                    Mean of the values currently stored in the Logger, including the current bin.
        """
        history = self.bin_series() #........................... Get the binned series of values
        total_sum = sum([value for (dt, value) in history]) #... Sum of all average values in the bins
        total_count = len(history) #............................ Count of bins in the history
        if total_count > 0:
            return total_sum / total_count #.................... Calculate and return the mean value
        else:
            return None #....................................... Return None if there are no values in the history
        
    def min(self):
        """
            Returns the minimum value currently stored in the Logger, including the current bin.

            Returns:
            --------
                float
                    Minimum value currently stored in the Logger, including the current bin.
        """
        history = self.bin_series() #........................... Get the binned series of values
        if len(history) > 0:
            return min([value for (dt, value) in history]) #.... Calculate and return the minimum value
        else:
            return None #....................................... Return None if there are no values in the history

    def max(self):
        """
            Returns the maximum value currently stored in the Logger, including the current bin.

            Returns:
            --------
                float
                    Maximum value currently stored in the Logger, including the current bin.
        """
        history = self.bin_series() #........................... Get the binned series of values
        if len(history) > 0:
            return max([value for (dt, value) in history]) #.... Calculate and return the maximum value
        else:
            return None #....................................... Return None if there are no values in the history
    
    def max_bin_history_sec(self):
        """
            Returns the maximum bin history length in seconds.

            Returns:
            --------
                float
                    Maximum bin history length in seconds.
        """
        return self.max_bin_history / 1000 #.................... Convert max_bin_history from ms to seconds and return it
    