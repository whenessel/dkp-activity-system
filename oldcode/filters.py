event_channels = [1,2,3,4]
guild_channels = [1,2,3,4,5,6,7,8]
list(filter(lambda channel: channel in event_channels, guild_channels))