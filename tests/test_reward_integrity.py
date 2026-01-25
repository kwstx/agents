import pytest
from environments.grid_world import GridWorld

class TestRewardIntegrity:
    def test_standard_step_penalty(self):
        """Verify standard step penalty is applied correctly."""
        env = GridWorld(size=5)
        env.reset()
        # Move internal state to center to avoid walls
        env.state = (2, 2)
        
        # Valid move
        _, reward, done, _ = env.step("UP")
        
        assert reward == -0.1, "Standard step should have -0.1 penalty"
        assert not done, "Standard step should not finish episode"

    def test_boundary_penalty(self):
        """Verify hitting a wall incurs larger penalty."""
        env = GridWorld(size=5)
        env.reset()
        env.state = (0, 0) # Bottom-left
        
        # Move Left (into wall)
        next_state, reward, done, _ = env.step("LEFT")
        
        assert next_state == (0, 0), "Agent should stay in place when hitting wall"
        assert reward == -1.0, "Wall hit should have -1.0 penalty"
        assert not done

    def test_goal_reward(self):
        """Verify reaching the goal yields positive reward and ends episode."""
        env = GridWorld(size=5)
        env.reset()
        # Place agent one step from goal
        goal_x, goal_y = env.goal
        env.state = (goal_x, goal_y - 1) 
        
        # Move UP into goal
        next_state, reward, done, _ = env.step("UP")
        
        assert next_state == env.goal, "Agent should be at goal"
        assert reward == 10.0, "Goal reached should have +10.0 reward"
        assert done, "Episode should be done upon reaching goal"

    def test_reward_distribution_sanity(self):
        """
        Run a random walk and ensure rewards are within expected discrete set.
        This validates we don't have unexpected 'noisy' rewards leaking in.
        """
        env = GridWorld(size=5)
        env.reset()
        
        allowed_rewards = {-0.1, -1.0, 10.0}
        
        import random
        actions = ["UP", "DOWN", "LEFT", "RIGHT"]
        
        for _ in range(100):
            action = random.choice(actions)
            _, reward, done, _ = env.step(action)
            assert reward in allowed_rewards, f"Unexpected reward value: {reward}"
            if done:
                env.reset()
