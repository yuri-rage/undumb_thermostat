# Undumb Thermostat Project

I have a Nest "smart home" thermostat because we are living in the future, and my comfort should approach the perpetual zen of Wall-E's La-Z-Boys with no more mental effort than it takes to believe in the power of Brawndo.

Instead, I wrote about 300 lines of Python to coerce the damn thing into achieving its life goals.

## A short (continued) rant...

Nest has a habit learning function that seems only to learn to annoy with nonsensical, poorly timed automatic settings.  It has an economy mode whose only job is to make you slightly yet perpetually uncomfortable.

It’s capable of providing MONTHS of historical data, explaining exactly why energy usage was better or worse during a given timeframe based on local weather conditions.  One might expect when purchasing overly expensive HAL 9000 doppelgänger wall art that it could use that same local weather data to enhance real time performance...but no-can-do, Dave.

One might attempt using [IFTTT](https://ifttt.com/home) to achieve a modicum of un-dumber thermostat-ing, but in 2019, Google decided to withdraw from IFTTT without rational thought, reasonable explanation, or viable alternative.  Isn't the future brilliant?!

But at least you'll probably pull only some of your hair out while creating the [Google Device Access Console](https://developers.google.com/nest/device-access) application that is required for the aforementioned 300 lines of code to unf*ck your little blue/red wall pill.  Fret not - there's about 50 lines of that code dedicated to keeping a few populated follicles on your skull during setup.

## Credit where it's due

Initially, I borrowed heavily from [Danielyaa5's therm-nest-command-line NodeJS project](https://github.com/danielyaa5/therm-nest-command-line).  It was super helpful to see how someone else navigated the twisted tangle of Google's device API, and I recommend his project if you simply need CLI access to your intellect lacking thermostat.

## Undumb your Nest

Before you begin, set your Nest to Heat/Cool mode, and turn Eco mode off.  If the script detects a mode other than Heat/Cool or that Eco mode is enabled, it will exit without making changes (assuming that you prefer the Nest's own dumb behavior).  If Heat/Cool mode is not available, the script won't work as written.

I wrote this script for use on a Raspberry Pi, but it should run equally well on Windows or Mac.  The instructions below are somewhat geared toward RPi use.

To use the script, first install the `requests` library with pip:

`pip install requests`

or, if you like:

`sudo pip install requests`

Place the script into a directory that makes sense (perhaps `/usr/local/bin`).  Run it with `python undumb.py` and follow the on screen prompts.

If you intend to run the script on an automated schedule (as it's intended), you may want to do the initial setup with `sudo` to give it access to the `/etc` directory.  You could also create a script user on your system if you don't want to run the script with root privileges, but that's beyond the scope of this documentation.

There are a lot of setup steps if you haven't used the Google Cloud Platform before, and it can be frustrating and confusing.  [This link](http://vunvulearadu.blogspot.com/2020/11/how-to-get-access-to-google-nest.html) is slightly outdated but may help clarify some of the steps.  Google is going to charge you a one-time fee of $5 as well, so there's that...

Once the script has successfully discovered your devices and created `secrets.json`, you can set up a [`systemd` service](https://linuxconfig.org/how-to-schedule-tasks-with-systemd-timers-in-linux) (or Windows Task) to run it a few times per day, or even hourly like I do.  Running it too often could re-dumb your thermostat, so stick to once per hour or so.

## secrets.json

This file contains all API keys and settings required for the script to undumb your Nest.  It isn't very secret.  Sorry.

All units are unapologetically Fahrenheit.  'Murica.

Most of the keys are self-explanatory.  Here's some additional explanation for those that aren't quite as clear by their names alone:
* `day_temp:` your preferred set temperature during daylight hours
* `night_temp:` your preferred set temperature during night hours
* `hysteresis:` the gap between the heat and cool set points - do not use less than 3.0
* `day_offset:` the number of minutes before/after sunrise that `day_temp` should be set
* `night_offset:` the number of minutes before/after sunset that `night_temp` should be set

The remainder of the device settings have to do with your house's behavior with respect to outside temperature and radiant heat from the sun.  The script will always use HEATCOOL mode to ensure that the indoor temperature never gets too far away from the desired set point.

When the outside temperature is cold, it will make the heat set point the desired indoor temperature and raise the cool set point to `hysteresis` degrees above that.  On the contrary, on a hot day, it will make the cool set point the desired indoor temperature and decrease the heat set point to `hysteresis` degrees below it.  This way, your thermostat is undumb, and the indoor temperature always remains close to the actual desired temperature (the script even accounts for indoor relative humidity and modifies the set point to a "feels like" value!).

To accurately determine the threshold at which the set point should be biased toward heating or cooling, you'll need to enter some information about your home's behavior with respect to outside temperature.  Most houses will require a bit of cooling even when the outdoor temperature is below the desired indoor temperature due to radiant heating from the sun as well as heat from indoor appliances or even people inside.

The script uses current temperature and UV index from OpenWeatherMap, along with the `*_uv_offset` values to determine the heat/cool bias threshold.  When the UV index is high, `max_uv_offset` will be subtracted from the set point to arrive at the threshold value.  When the UV index is low, `min_uv_offset` will be used the same way.  `mid_uv_index` is used to further modify the threshold in an attempt to account for latent heat in the evening and cooler temperatures in the morning.  Evening and morning in this case are defined by `morning_offset` and `evening_offset` (in minutes).  The script will delay applying a large UV offset in the morning and likewise continue applying a larger UV offset in the evening.

If that doesn't make sense, just use the default values and keep an eye on your house's behavior when the outside temperature swings above and below the desired indoor temperature (like Spring and Fall in most locales).  If the script isn't being smart enough, modify the UV offset values and/or morning/evening offset values to suit.

Long story short, I guess you have to be smart enough to undumb your thermostat, lest this script just make it dumber.