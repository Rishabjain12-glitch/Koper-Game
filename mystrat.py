"""
To understand deeply how to use this functions and all the variables given please look at the dummy_strategies.py file.

You have to implement your strategy in this file. 

Change the class name (i.e YourStrategyName) with your team name. 
Also change same name in dummy_strategies.py file (where imports are being done)
"""


class YourStrategyName:
    """
    Advanced KOPER Strategy with:
    - Dynamic fold thresholds
    - Equity trend tracking
    - Opponent modeling
    - Winning cap optimization
    - Stack management
    
    IMPORTANT: Change 'YourStrategyName' to your team name and update line 387 in dummy_strategies.py
    """
    
    def __init__(self):
        # Initialize any state variables here.
        # This is where your unique index for the CURRENT match will be stored.
        self.my_index = -1
        
        # Opponent tracking
        self.opponent_profiles = {}
        
        # Per-game state
        self.games_played = 0
        self.prev_win_prob_r1 = None
        self.prev_win_prob_r2 = None
    
    def initialize_game(self, match_history, current_game_num):
        """
        Update Opponent Profiles (only if new data exists)
        """
        self.games_played = current_game_num
        
        # Reset per-game tracking
        self.prev_win_prob_r1 = None
        self.prev_win_prob_r2 = None
        
        # Initialize opponent profiles on first game
        if current_game_num == 1:
            for i in range(5):
                if i != self.my_index:
                    self.opponent_profiles[i] = {
                        "games_seen": 0,
                        "games_played": 0,
                        "fold_count": 0,
                        "total_r1_bets": 0
                    }
            return
        
        # Update profiles from last completed game
        if len(match_history) > 0:
            last_game = match_history[-1]
            
            for pid, pdata in last_game.items():
                if isinstance(pid, int) and pid != self.my_index:
                    profile = self.opponent_profiles.get(pid)
                    if profile is None:
                        continue
                    
                    profile["games_seen"] += 1
                    
                    if pdata.get("folded", False):
                        profile["fold_count"] += 1
                    else:
                        profile["games_played"] += 1
    
    # --- ROUND 1 (Pre-Flop) ---
    def round1(self, hole, comm, stacks, pot, win_prob):
        """
        CRUCIAL INFO:
        Your unique index for the current game is available via: self.my_index
        Use it to access your stack and your previous bets:
        - stacks[self.my_index]
        
        Returns: ("fold", 0) OR ("play", bet_amount)
        """
        my_stack = stacks[self.my_index]
        
        # Store for Round 2 comparison
        self.prev_win_prob_r1 = win_prob
        
        # Dynamic fold threshold based on stack size
        if my_stack < 500:
            fold_threshold = 0.25  # Very tight when desperate
        elif my_stack < 1000:
            fold_threshold = 0.20  # Tight when short-stacked
        else:
            fold_threshold = 0.15  # Normal threshold
        
        # Tighten up near end of tournament
        if self.games_played > 40:
            fold_threshold += 0.05
        
        # FOLD DECISION
        if win_prob < fold_threshold:
            return "fold", 0
        
        # BETTING STRATEGY based on stack size and win probability
        if my_stack < 500:
            # Critical stack: ultra conservative
            if win_prob < 0.4:
                bet = 100.0
            elif win_prob < 0.7:
                bet = 150.0
            else:
                bet = 200.0
        elif my_stack < 1000:
            # Short stack: conservative
            if win_prob < 0.5:
                bet = 100.0 + (win_prob * 100)
            else:
                bet = 150.0 + (win_prob * 150)
        else:
            # Healthy stack: normal value betting
            if win_prob < 0.4:
                bet = 100.0 + (win_prob * 150)
            elif win_prob < 0.7:
                bet = 180.0 + (win_prob * 120)
            else:
                # Strong hand: maximize value
                bet = 270.0 + (win_prob * 30)
        
        # Ensure bet is in valid range [100, 300]
        bet = max(100.0, min(300.0, bet))
        
        # Don't bet more than we have
        bet = min(bet, my_stack)
        
        return "play", bet
    
    # --- ROUND 2 (Flop/Turn) ---
    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        """
        Args:
            r1_bets (dict): R1 bets {player_index: bet_amount}.
        
        Returns:
            float: Desired bet amount.
        """
        my_stack = stacks[self.my_index]
        my_r1_bet = r1_bets[self.my_index]
        
        # Store for Round 3 comparison
        self.prev_win_prob_r2 = win_prob
        
        # Calculate allowed betting range: 0.5x to 1.5x of R1 bet
        min_bet = my_r1_bet * 0.5
        max_bet = my_r1_bet * 1.5
        
        # Check if equity improved from Round 1
        equity_improved = False
        if self.prev_win_prob_r1 is not None:
            equity_change = win_prob - self.prev_win_prob_r1
            equity_improved = equity_change > 0.05  # Significant improvement
        
        # Count how many opponents bet high in R1
        num_high_bettors = sum(
            1 for pid, bet in r1_bets.items() 
            if pid != self.my_index and bet > 200
        )
        
        # Base multiplier on current win probability
        if win_prob > 0.75:
            multiplier = 1.4
        elif win_prob > 0.6:
            multiplier = 1.3
        elif win_prob > 0.45:
            multiplier = 1.0
        elif win_prob > 0.3:
            multiplier = 0.7
        else:
            multiplier = 0.5
        
        # Adjust for equity trend
        if equity_improved and win_prob > 0.5:
            multiplier += 0.1  # Hand improved, bet more
        elif self.prev_win_prob_r1 and (win_prob < self.prev_win_prob_r1 - 0.1):
            multiplier -= 0.1  # Hand got worse, bet less
        
        # Adjust for pot size
        if pot > 1500 and win_prob > 0.6:
            multiplier += 0.1  # Extract more value from big pots
        
        # Adjust for opponent aggression
        if num_high_bettors >= 2 and win_prob < 0.5:
            multiplier -= 0.1  # Be cautious against multiple aggressive players
        
        # Calculate bet
        bet = my_r1_bet * multiplier
        
        # Clamp to allowed range
        bet = max(min_bet, min(max_bet, bet))
        
        # Don't exceed our stack
        bet = min(bet, my_stack)
        
        return bet
    
    # --- ROUND 3 (River) ---
    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        """
        Args:
            r2_bets (dict): R2 bets {player_index: bet_amount}.
        
        Returns:
            float: Desired bet amount.
        """
        my_stack = stacks[self.my_index]
        my_r1_bet = r1_bets[self.my_index]
        my_r2_bet = r2_bets[self.my_index]
        
        # Calculate allowed betting range: 0.75x to 1.25x of R2 bet
        min_bet = my_r2_bet * 0.75
        max_bet = my_r2_bet * 1.25
        
        # Calculate total contribution so far (before R3 bet)
        my_contribution = 100 + my_r1_bet + my_r2_bet  # BUY_IN + R1 + R2
        
        # Check if equity improved from Round 2
        equity_improved = False
        if self.prev_win_prob_r2 is not None:
            equity_improved = (win_prob - self.prev_win_prob_r2) > 0.05
        
        # WINNING CAP OPTIMIZATION
        # Maximum we can win = 4 * (total contribution including R3 bet)
        if win_prob > 0.7:
            # Calculate current winning cap (without R3 bet)
            current_cap = 4 * my_contribution
            
            if current_cap > pot:
                # Already over-capped, minimize risk by betting minimum
                multiplier = 0.75
            else:
                # Need more contribution to cover the pot
                needed_contribution = pot / 4
                needed_r3_bet = needed_contribution - my_contribution
                
                # Convert to multiplier
                if needed_r3_bet <= min_bet:
                    multiplier = 0.75
                elif needed_r3_bet >= max_bet:
                    multiplier = 1.25
                else:
                    multiplier = needed_r3_bet / my_r2_bet
                    multiplier = max(0.75, min(1.25, multiplier))
        else:
            # Standard betting based on hand strength
            if win_prob > 0.8:
                multiplier = 1.25  # Extremely strong
            elif win_prob > 0.6:
                # Strong hand: scale from 1.0 to 1.25
                multiplier = 1.0 + ((win_prob - 0.6) / 0.2) * 0.25
            elif win_prob > 0.4:
                multiplier = 1.0  # Medium hand
            elif win_prob > 0.25:
                multiplier = 0.85  # Weak hand
            else:
                multiplier = 0.75  # Very weak - minimize loss
        
        # Adjust for equity trend
        if equity_improved and win_prob > 0.6:
            multiplier = min(1.25, multiplier + 0.05)
        elif not equity_improved and win_prob < 0.5:
            multiplier = max(0.75, multiplier - 0.05)
        
        # Calculate final bet
        bet = my_r2_bet * multiplier
        
        # Clamp to allowed range
        bet = max(min_bet, min(max_bet, bet))
        
        # Don't exceed our stack
        bet = min(bet, my_stack)
        
        return bet


# ============================================================
# OPTIONAL: Additional Strategies for Testing
# ============================================================

class Strategy2:
    """Conservative Strategy - Focuses on survival and minimizing losses"""
    
    def __init__(self):
        self.my_index = -1
    
    def initialize_game(self, match_history, current_game_num):
        pass
    
    def round1(self, hole, comm, stacks, pot, win_prob):
        my_stack = stacks[self.my_index]
        
        # Very tight folding
        if win_prob < 0.20:
            return "fold", 0
        
        # Conservative betting
        if my_stack < 1000:
            if win_prob < 0.35:
                return "fold", 0
            return "play", 100.0
        
        bet = 100.0 + (win_prob * 150)
        return "play", min(250.0, bet)
    
    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        my_r1_bet = r1_bets[self.my_index]
        
        if win_prob > 0.7:
            multiplier = 1.3
        elif win_prob > 0.5:
            multiplier = 1.0
        else:
            multiplier = 0.6
        
        bet = my_r1_bet * multiplier
        bet = max(my_r1_bet * 0.5, min(my_r1_bet * 1.5, bet))
        return min(bet, stacks[self.my_index])
    
    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        my_r2_bet = r2_bets[self.my_index]
        
        if win_prob > 0.75:
            multiplier = 1.2
        elif win_prob > 0.5:
            multiplier = 1.0
        else:
            multiplier = 0.75
        
        bet = my_r2_bet * multiplier
        bet = max(my_r2_bet * 0.75, min(my_r2_bet * 1.25, bet))
        return min(bet, stacks[self.my_index])


class Strategy3:
    """Aggressive Strategy - Maximizes value with calculated risks"""
    
    def __init__(self):
        self.my_index = -1
    
    def initialize_game(self, match_history, current_game_num):
        pass
    
    def round1(self, hole, comm, stacks, pot, win_prob):
        if win_prob < 0.12:
            return "fold", 0
        
        if win_prob > 0.65:
            bet = 280.0 + (win_prob * 20)
        elif win_prob > 0.45:
            bet = 200.0 + (win_prob * 100)
        else:
            bet = 120.0 + (win_prob * 150)
        
        return "play", max(100.0, min(300.0, bet))
    
    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        my_r1_bet = r1_bets[self.my_index]
        
        if win_prob > 0.65:
            multiplier = 1.5
        elif win_prob > 0.45:
            multiplier = 1.2
        else:
            multiplier = 0.7
        
        bet = my_r1_bet * multiplier
        bet = max(my_r1_bet * 0.5, min(my_r1_bet * 1.5, bet))
        return min(bet, stacks[self.my_index])
    
    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        my_r2_bet = r2_bets[self.my_index]
        
        if win_prob > 0.7:
            multiplier = 1.25
        elif win_prob > 0.5:
            multiplier = 1.1
        else:
            multiplier = 0.8
        
        bet = my_r2_bet * multiplier
        bet = max(my_r2_bet * 0.75, min(my_r2_bet * 1.25, bet))
        return min(bet, stacks[self.my_index])


class Strategy4:
    """Adaptive Strategy - Uses opponent modeling from match history"""
    
    def __init__(self):
        self.my_index = -1
        self.opponent_looseness = {}
    
    def initialize_game(self, match_history, current_game_num):
        if current_game_num == 1:
            for i in range(5):
                if i != self.my_index:
                    self.opponent_looseness[i] = {"played": 0, "seen": 0}
            return
        
        if len(match_history) > 0:
            last_game = match_history[-1]
            for pid, pdata in last_game.items():
                if isinstance(pid, int) and pid != self.my_index:
                    profile = self.opponent_looseness.get(pid)
                    if profile:
                        profile["seen"] += 1
                        if not pdata.get("folded", False):
                            profile["played"] += 1
    
    def get_table_looseness(self):
        total_rate = 0
        count = 0
        for profile in self.opponent_looseness.values():
            if profile["seen"] > 0:
                total_rate += profile["played"] / profile["seen"]
                count += 1
        return total_rate / count if count > 0 else 0.5
    
    def round1(self, hole, comm, stacks, pot, win_prob):
        table_looseness = self.get_table_looseness()
        
        if table_looseness < 0.3:
            fold_threshold = 0.12
        else:
            fold_threshold = 0.18
        
        if win_prob < fold_threshold:
            return "fold", 0
        
        if table_looseness > 0.4:
            bet = 200.0 + (win_prob * 100)
        else:
            bet = 120.0 + (win_prob * 150)
        
        return "play", max(100.0, min(300.0, bet))
    
    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        my_r1_bet = r1_bets[self.my_index]
        multiplier = 0.5 + (win_prob * 1.0)
        bet = my_r1_bet * multiplier
        bet = max(my_r1_bet * 0.5, min(my_r1_bet * 1.5, bet))
        return min(bet, stacks[self.my_index])
    
    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        my_r2_bet = r2_bets[self.my_index]
        multiplier = 0.75 + (win_prob * 0.5)
        bet = my_r2_bet * multiplier
        bet = max(my_r2_bet * 0.75, min(my_r2_bet * 1.25, bet))
        return min(bet, stacks[self.my_index])


class Strategy5:
    """Balanced Strategy - Equity tracking with stack awareness"""
    
    def __init__(self):
        self.my_index = -1
        self.prev_win_prob = None
    
    def initialize_game(self, match_history, current_game_num):
        self.prev_win_prob = None
    
    def round1(self, hole, comm, stacks, pot, win_prob):
        self.prev_win_prob = win_prob
        my_stack = stacks[self.my_index]
        
        fold_threshold = 0.20 if my_stack < 800 else 0.15
        
        if win_prob < fold_threshold:
            return "fold", 0
        
        if win_prob > 0.7:
            bet = 250.0 + (win_prob * 50)
        elif win_prob > 0.5:
            bet = 180.0 + (win_prob * 120)
        else:
            bet = 100.0 + (win_prob * 160)
        
        return "play", max(100.0, min(300.0, bet))
    
    def round2(self, hole, comm, r1_bets, stacks, pot, win_prob):
        my_r1_bet = r1_bets[self.my_index]
        
        if self.prev_win_prob and win_prob > self.prev_win_prob:
            multiplier = 1.3
        else:
            multiplier = 0.5 + (win_prob * 1.0)
        
        self.prev_win_prob = win_prob
        bet = my_r1_bet * multiplier
        bet = max(my_r1_bet * 0.5, min(my_r1_bet * 1.5, bet))
        return min(bet, stacks[self.my_index])
    
    def round3(self, hole, comm, r1_bets, r2_bets, stacks, pot, win_prob):
        my_r2_bet = r2_bets[self.my_index]
        
        if win_prob > 0.75:
            multiplier = 1.25
        elif win_prob > 0.55:
            multiplier = 1.1
        else:
            multiplier = 0.8
        
        bet = my_r2_bet * multiplier
        bet = max(my_r2_bet * 0.75, min(my_r2_bet * 1.25, bet))
        return min(bet, stacks[self.my_index])
