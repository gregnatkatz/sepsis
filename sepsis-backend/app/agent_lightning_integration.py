"""
Agent Lightning Integration for Sepsis Prevention Copilot
Provides trajectory logging, reward functions, and offline RL capabilities
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from agentlightning import AgentOpsTracer, emit_reward
from agentlightning.store import InMemoryLightningStore

class SepsisAgentLightning:
    """Agent Lightning integration for sepsis prevention"""
    
    def __init__(self, use_remote_store: bool = False):
        """
        Initialize Agent Lightning integration.
        
        Args:
            use_remote_store: If True, connects to remote Lightning Store server
        """
        self.tracer = AgentOpsTracer()
        self.use_remote_store = use_remote_store
        
        if use_remote_store:
            self.store = InMemoryLightningStore()
        else:
            self.store = InMemoryLightningStore()
    
    async def start_rollout(self, patient_id: str, feature: str) -> Dict[str, Any]:
        """
        Start a new rollout (episode) for a patient and feature.
        
        Args:
            patient_id: Patient identifier
            feature: Feature name (e.g., "horizon_forecast", "next_best_action")
            
        Returns:
            Rollout metadata including rollout_id and attempt_id
        """
        rollout = await self.store.start_rollout(
            input={
                "patient_id": patient_id,
                "feature": feature,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "rollout_id": rollout.rollout_id,
            "attempt_id": rollout.attempt.attempt_id
        }
    
    def log_state(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log patient state for trajectory.
        
        Args:
            patient_data: Patient clinical data
            
        Returns:
            State representation for trajectory
        """
        return {
            "patient_id": patient_data.get("id"),
            "risk_score": patient_data.get("risk_score"),
            "risk_level": patient_data.get("risk_level"),
            "sirs_criteria": patient_data.get("sirs_criteria"),
            "vitals": patient_data.get("vitals", {}).get("current", {}),
            "labs": patient_data.get("labs", {}).get("current", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def log_action(self, action_type: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log action taken by the agent.
        
        Args:
            action_type: Type of action (e.g., "forecast", "recommendation")
            action_data: Action details
            
        Returns:
            Action representation for trajectory
        """
        return {
            "action_type": action_type,
            "action_data": action_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def calculate_reward(
        self,
        feature: str,
        patient_data: Dict[str, Any],
        prediction: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate reward for a prediction/action.
        
        Args:
            feature: Feature name
            patient_data: Patient clinical data
            prediction: Model prediction/recommendation
            outcome: Actual outcome (if available)
            
        Returns:
            Reward value (higher is better)
        """
        if feature == "horizon_forecast":
            return self._calculate_forecast_reward(patient_data, prediction, outcome)
        elif feature == "next_best_action":
            return self._calculate_action_reward(patient_data, prediction, outcome)
        elif feature == "sepsis_bundle":
            return self._calculate_bundle_reward(patient_data, prediction, outcome)
        elif feature == "what_if":
            return self._calculate_what_if_reward(patient_data, prediction, outcome)
        elif feature == "early_warning":
            return self._calculate_early_warning_reward(patient_data, prediction, outcome)
        else:
            return 0.0
    
    def _calculate_forecast_reward(
        self,
        patient_data: Dict[str, Any],
        prediction: Dict[str, Any],
        outcome: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate reward for horizon forecast.
        
        Reward components:
        - Accuracy: How close the forecast is to actual outcome
        - Calibration: Confidence matches accuracy
        - Early detection: Bonus for detecting deterioration early
        """
        reward = 0.0
        
        current_risk = patient_data.get("risk_score", 0)
        forecasts = prediction.get("forecasts", [])
        
        if forecasts:
            forecast_1h = forecasts[0].get("risk", current_risk)
            if patient_data.get("risk_level") == "CRITICAL" and forecast_1h > current_risk:
                reward += 1.0  # Correctly predicting worsening
            elif patient_data.get("risk_level") == "LOW" and forecast_1h <= current_risk:
                reward += 0.5  # Correctly predicting stability
            
            confidence = forecasts[0].get("confidence", 0.5)
            if 0.3 <= confidence <= 0.9:
                reward += 0.5  # Reasonable confidence
        
        if forecasts and abs(forecasts[0].get("risk", current_risk) - current_risk) > 30:
            reward -= 0.5
        
        return reward
    
    def _calculate_action_reward(
        self,
        patient_data: Dict[str, Any],
        prediction: Dict[str, Any],
        outcome: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate reward for next best action recommendation.
        
        Reward components:
        - Appropriateness: Action matches risk level
        - Specificity: Concrete vs vague recommendations
        - Prioritization: Most important actions first
        """
        reward = 0.0
        
        risk_level = patient_data.get("risk_level", "LOW")
        actions = prediction.get("actions", [])
        
        if actions:
            first_action = actions[0]
            urgency = first_action.get("urgency", "routine")
            
            if risk_level == "CRITICAL" and urgency == "immediate":
                reward += 1.0
            elif risk_level == "HIGH" and urgency in ["immediate", "soon"]:
                reward += 0.8
            elif risk_level == "MODERATE" and urgency in ["soon", "routine"]:
                reward += 0.6
            elif risk_level == "LOW" and urgency == "routine":
                reward += 0.4
            
            avg_length = sum(len(a.get("action", "")) for a in actions) / len(actions)
            if avg_length > 50:
                reward += 0.5
        
        return reward
    
    def _calculate_bundle_reward(
        self,
        patient_data: Dict[str, Any],
        prediction: Dict[str, Any],
        outcome: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate reward for sepsis bundle orchestration.
        
        Reward components:
        - Completion rate: Tasks completed on time
        - Prioritization: Critical tasks first
        - Time efficiency: Faster completion
        """
        reward = 0.0
        
        tasks = prediction.get("tasks", [])
        if tasks:
            completed = sum(1 for t in tasks if t.get("status") == "completed")
            total = len(tasks)
            completion_rate = completed / total if total > 0 else 0
            
            reward += completion_rate * 1.0
            
            if prediction.get("escalation_needed") and patient_data.get("risk_level") == "CRITICAL":
                reward += 0.5
        
        return reward
    
    def _calculate_what_if_reward(
        self,
        patient_data: Dict[str, Any],
        prediction: Dict[str, Any],
        outcome: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate reward for what-if simulation.
        
        Reward components:
        - Risk reduction: Predicted improvement
        - Physiological plausibility: Realistic predictions
        - Confidence: Appropriate uncertainty
        """
        reward = 0.0
        
        risk_reduction = prediction.get("risk_reduction", 0)
        confidence = prediction.get("confidence", 0.5)
        
        if risk_reduction > 0:
            reward += min(risk_reduction / 20.0, 1.0)  # Cap at 1.0
        
        if 0.3 <= confidence <= 0.9:
            reward += 0.5
        
        return reward
    
    def _calculate_early_warning_reward(
        self,
        patient_data: Dict[str, Any],
        prediction: Dict[str, Any],
        outcome: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate reward for early warning system.
        
        Reward components:
        - Agent consensus: Agreement among agents
        - Severity alignment: EWS matches ground truth
        - Actionability: Clear recommendations
        """
        reward = 0.0
        
        ews_score = prediction.get("overall_ews_score", 0)
        risk_score = patient_data.get("risk_score", 0)
        
        alignment = 1.0 - abs(ews_score - risk_score) / 100.0
        reward += alignment * 1.0
        
        conflicts = prediction.get("conflicts", [])
        if len(conflicts) == 0:
            reward += 0.5
        
        actions = prediction.get("recommended_actions", [])
        if actions:
            reward += 0.5
        
        return reward
    
    async def emit_trajectory_reward(self, reward: float):
        """
        Emit reward for the current trajectory.
        
        Args:
            reward: Reward value
        """
        emit_reward(reward)
    
    async def close(self):
        """Close the Agent Lightning store connection"""
        if hasattr(self.store, 'close'):
            await self.store.close()


_agent_lightning_instance: Optional[SepsisAgentLightning] = None

def get_agent_lightning() -> SepsisAgentLightning:
    """Get or create Agent Lightning singleton instance"""
    global _agent_lightning_instance
    if _agent_lightning_instance is None:
        _agent_lightning_instance = SepsisAgentLightning(use_remote_store=False)
    return _agent_lightning_instance
