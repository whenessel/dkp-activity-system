# TODO: Этот способ имеет проблемы при большом количестве одновременных реакциях
# Проверяем установку только одной реакции
for reaction in message.reactions:
    if member in [user async for user in reaction.users()] \
            and not payload.member.bot \
            and str(reaction) != str(payload.emoji) \
            and str(reaction) not in ModeratorReactions.emojis():
        print("TOGGLE REACTION", reaction.emoji, payload.member)
        await message.remove_reaction(reaction.emoji, payload.member)