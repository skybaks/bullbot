def up(cursor, bot):
    # Useful query for deleting duplicate games:
    # DELETE FROM bet_game a WHERE a.ctid <> (SELECT min(b.ctid) FROM bet_game b WHERE a.internal_id = b.internal_id);

    # bet_game.internal_id +UNIQUE, -NOT NULL
    cursor.execute("ALTER TABLE bet_game ALTER COLUMN internal_id DROP NOT NULL")
    cursor.execute("ALTER TABLE bet_game ADD UNIQUE(internal_id)")

    # new: bet_game.bet_closed
    cursor.execute("ALTER TABLE bet_game ADD COLUMN bets_closed BOOL")

    # bet_game.outcome, points_change, win_bettors, loss_bettors: -NOT NULL
    cursor.execute("ALTER TABLE bet_game ALTER COLUMN outcome DROP NOT NULL")
    cursor.execute("ALTER TABLE bet_game ALTER COLUMN points_change DROP NOT NULL")
    cursor.execute("ALTER TABLE bet_game ALTER COLUMN win_bettors DROP NOT NULL")
    cursor.execute("ALTER TABLE bet_game ALTER COLUMN loss_bettors DROP NOT NULL")

    # bet_game: Check that either both trackobot_id and outcome are NULL, or both are not.
    cursor.execute(
        "ALTER TABLE bet_game ADD CHECK ((internal_id IS NULL AND outcome is NULL) OR (internal_id IS NOT NULL AND outcome is NOT NULL))"
    )

    # bet_bet.game_id: add ON DELETE CASCADE
    cursor.execute("ALTER TABLE bet_bet DROP CONSTRAINT bet_bet_game_id_fkey")
    cursor.execute("ALTER TABLE bet_bet ADD FOREIGN KEY (game_id) REFERENCES bet_game(id) ON DELETE CASCADE")

    # bet_bet: Remove id column, add combined primary key
    cursor.execute("ALTER TABLE bet_bet DROP CONSTRAINT bet_bet_pkey")
    cursor.execute("ALTER TABLE bet_bet DROP COLUMN id")
    cursor.execute("ALTER TABLE bet_bet ADD PRIMARY KEY (game_id, user_id)")

    # bet_bet.profit: -NOT NULL
    cursor.execute("ALTER TABLE bet_bet ALTER COLUMN profit DROP NOT NULL")
