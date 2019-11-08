def up(cursor, bot):
    cursor.execute("ALTER TABLE dotabet_bet RENAME TO bet_bet")
    cursor.execute("ALTER TABLE dotabet_game RENAME TO bet_game")
    cursor.execute("ALTER TYPE dotabet_outcome RENAME TO bet_outcome")
