import time

class Logger:
    """
    Logger for time-series sensor data. Maintains a history of samples within a specified
    time window and provides binned averages for plotting. Designed for use in a microcontroller
    environment with limited resources. Handles time using ticks_ms and accounts for wrap-around.
    """
    def __init__(self, timedelta_seconds, dt_seconds):
        """
            Initialize the Logger.

            Arguments:
            ----------
                timedelta_seconds: float
                    Length of the history window in seconds (e.g., 3600 for 1 hour)
                dt_seconds: float
                    Bin width for output in seconds (e.g., 60 for 1-minute bins)
            
            Returns:
            --------
                None
                   This function initializes the Logger and does not return any value.
        """
    #-- Save attributes ------------------------------------------------
        self.timedelta_ms = int(timedelta_seconds * 1000)
        self.dt_ms = int(dt_seconds * 1000)
    #-- Internal data storage ------------------------------------------
        self._data = [] #................ list of dicts: {"t": ticks_ms, "p":..., "tC":..., "h":..., "co2":...}
    #-- Return ---------------------------------------------------------
        return

    def add_sample(self, pressure, temperature, humidity, co2):
        """
            Add a new sample of sensor data with the current timestamp.

            Arguments:
            ----------
                pressure: float
                    Pressure in hPa
                temperature: float
                    Temperature in Celsius
                humidity: float
                    Humidity in percentage
                co2: float
                    CO2 concentration in ppm (parts per million)
            
            Returns:
            --------
                None
                   This function adds a new sample to the Logger
                   and does not return any value.
        """
        now = time.ticks_ms() #...................... Current time in ms
        self._data.append({
                    "t": now,
                    "p": pressure,
                    "tC": temperature,
                    "h": humidity,
                    "co2": co2,
                }) #................................. Add new sample to data list
        self._prune_old(now) #....................... Remove old samples outside the time window
    #-- Return ---------------------------------------------------------
        return

    def _prune_old(self, now):
        """
            Remove samples older than timedelta_ms from now.

            Arguments:
            ----------
                now: int
                    Current time in ticks_ms
            
            Returns:
            --------
                None
                   This function prunes old samples from the Logger
                   and does not return any value.
        """
        cutoff = time.ticks_add(now, -self.timedelta_ms) #..... Calculate cutoff time; samples older than this should be removed
    #-- Iterate through data and keep only samples newer than cutoff ---
        i = 0
        n = len(self._data)
        while i < n:
            # Calculate age of sample in ms using ticks_diff to handle wrap-around
            age_ms = time.ticks_diff(self._data[i]["t"], cutoff)
            # if sample time < cutoff, ticks_diff will be negative
            if age_ms < 0:
                i += 1
            else:
                break
        if i > 0:
            self._data = self._data[i:]
    #-- Return ---------------------------------------------------------
        return

    def _bin_series(self, key):
        """
            Return [[dt_seconds_ago, avg_value], ...] for a given field key.
            
            Arguments:
            ----------
                key: str
                    One of "p", "tC", "h", "co2" corresponding to pressure,
                    temperature, humidity, and CO2.
            
            Returns:
            --------
                list of [dt_seconds_ago, avg_value]
                    A list of pairs where dt_seconds_ago is the age of the
                    bin center in seconds (0 for now, positive for past)
                    and avg_value is the average of the specified key for
                    samples in that bin. Bins are of width dt_seconds and
                    cover the last timedelta_seconds.
        """
        if not self._data:
            return []

        now = time.ticks_ms() #...................... Current time in ms

        # Compute age in ms for each sample (0 for newest, positive for older)
        # age_ms = now - t_sample, using ticks_diff to handle wrap-around.
        ages = [time.ticks_diff(now, s["t"]) for s in self._data]

        # Oldest and newest ages
        oldest_age = ages[0]
        newest_age = ages[-1]

        # We want bins from age=0 (now) up to age=timedelta_ms, in steps of
        # dt_ms. But data may not fill all bins.
        max_age = min(self.timedelta_ms, oldest_age)
        n_bins = max_age // self.dt_ms + 1

        # Prepare accumulators
        sums = [0.0] * n_bins
        counts = [0] * n_bins

        # Assign each sample to a bin based on age
        for age_ms, s in zip(ages, self._data):
            if age_ms < 0 or age_ms > self.timedelta_ms:
                continue  # should not happen if pruning works, but be safe
            bin_index = age_ms // self.dt_ms
            if bin_index >= n_bins:
                continue
            sums[bin_index] += s[key]
            counts[bin_index] += 1

        # Build result: timedelta in seconds (from now), average value
        result = []
        for i in range(n_bins):
            if counts[i] == 0:
                continue  # skip empty bins; alternatively, emit None or 0
            # bin center age in ms, from now
            bin_age_center_ms = i * self.dt_ms + self.dt_ms // 2
            dt_sec = bin_age_center_ms / 1000.0
            avg_val = sums[i] / counts[i]
            result.append([dt_sec, avg_val])

        return result

    def get_pressure(self):
        """
            Returns pressure data as a binned list of
            [dt_seconds_ago, avg_pressure] pairs for plotting.
        """
        return self._bin_series("p")

    def get_temperature(self):
        """
            Returns temperature data as a binned list of
            [dt_seconds_ago, avg_temperature] pairs for plotting.
        """
        return self._bin_series("tC")

    def get_humidity(self):
        """
            Returns humidity data as a binned list of
            [dt_seconds_ago, avg_humidity] pairs for plotting.
        """
        return self._bin_series("h")

    def get_co2(self):
        """
            Returns CO2 data as a binned list of
            [dt_seconds_ago, avg_co2] pairs for plotting.
        """
        return self._bin_series("co2")
