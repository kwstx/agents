from .base_env import BaseEnvironment

class RoboticsSim(BaseEnvironment):
    """
    A simple example environment simulating a robot arm.
    """
    def __init__(self, joint_count: int = 3):
        self.joint_count = joint_count
        self.joints = [0.0] * joint_count

    def get_state(self):
        return {"joints": self.joints}

    def step(self, action):
        """
        Action format: {'joint_index': int, 'delta': float}
        """
        joint_idx = action.get("joint_index")
        delta = action.get("delta", 0.0)

        if joint_idx is not None and 0 <= joint_idx < self.joint_count:
            self.joints[joint_idx] += delta
        
        return self.get_state()
    
    def reset(self):
        self.joints = [0.0] * self.joint_count
        return self.get_state()
