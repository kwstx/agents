import time
import torch
import psutil
import os
import numpy as np
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer

class PerformanceBenchmark:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.config = ModelConfig()
        self.model = GridDecisionModel(self.config)
        self.trainer = DQNTrainer(self.model, self.config)
        
    def measure_inference_latency(self, iterations=1000):
        input_tensor = torch.rand(1, 4)
        
        # Warmup
        for _ in range(100):
            self.model(input_tensor)
            
        start_time = time.perf_counter()
        for _ in range(iterations):
            with torch.no_grad():
                self.model(input_tensor)
        end_time = time.perf_counter()
        
        avg_latency_ms = ((end_time - start_time) / iterations) * 1000
        print(f"Inference Latency: {avg_latency_ms:.4f} ms")
        return avg_latency_ms

    def measure_training_latency(self, iterations=1000):
        # Fill buffer
        state = [0.1, 0.2, 0.8, 0.8]
        next_state = [0.1, 0.3, 0.8, 0.8]
        for _ in range(self.trainer.batch_size + 5):
            self.trainer.store_experience(state, 0, 1.0, next_state, False)
            
        # Warmup
        for _ in range(10):
            self.trainer.train_step()
            
        start_time = time.perf_counter()
        for _ in range(iterations):
            self.trainer.train_step()
        end_time = time.perf_counter()
        
        avg_latency_ms = ((end_time - start_time) / iterations) * 1000
        print(f"Training Step Latency: {avg_latency_ms:.4f} ms")
        return avg_latency_ms

    def measure_resource_usage(self):
        # Baseline
        mem_rss_start = self.process.memory_info().rss / (1024 * 1024)
        cpu_start = self.process.cpu_percent(interval=None)
        
        # Intensive workload
        self.measure_inference_latency(5000)
        self.measure_training_latency(5000)
        
        mem_rss_end = self.process.memory_info().rss / (1024 * 1024)
        cpu_end = self.process.cpu_percent(interval=None)
        
        delta_mem = mem_rss_end - mem_rss_start
        print(f"Memory Usage (RSS): {mem_rss_end:.2f} MB (Delta: {delta_mem:.2f} MB)")
        print(f"CPU Usage: {cpu_end:.1f}% (Process)")
        
        return mem_rss_end, cpu_end

if __name__ == "__main__":
    print("--- Starting Performance Benchmark ---")
    benchmark = PerformanceBenchmark()
    
    inf_latency = benchmark.measure_inference_latency()
    train_latency = benchmark.measure_training_latency()
    mem_usage, cpu_usage = benchmark.measure_resource_usage()
    
    # Assertions for "Laptop-Ready" MVP
    # Inference should be extremely fast for simple MLP (< 5ms)
    assert inf_latency < 5.0, f"Inference too slow: {inf_latency} ms"
    
    # Training step (batch 64) should be reasonably fast (< 20ms)
    assert train_latency < 20.0, f"Training too slow: {train_latency} ms"
    
    # Memory footprint should be small (< 500MB total, usually much less for this size)
    assert mem_usage < 500, f"Memory usage too high: {mem_usage} MB"
    
    print("\nSUCCESS: Performance implies lightweight laptop compatibility.")
