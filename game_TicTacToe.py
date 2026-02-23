import games
# Main function
game_object = games.TicTacToe()
game_object.play_game(games.minmax_player, games.random_player)