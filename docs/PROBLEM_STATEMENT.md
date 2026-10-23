# Problem statement

## Title
**EdgeAI: Multi-User Local LLM Inference and Serving System Using NVIDIA Jetson**
(alternative: *EdgeServe AI: Optimized Multi-User LLM Serving on Resource-Constrained Edge Devices*)

## Problem
Most LLM applications depend on centralized cloud infrastructure. That brings network latency,
recurring cost, privacy concerns and a hard dependency on internet connectivity.

Running an LLM locally on an NVIDIA Jetson removes many of those dependencies but creates new
problems: very limited memory shared between CPU and GPU, modest GPU throughput, and the need to
serve several users at once without loading a separate copy of the model for each of them.

## Aim
Build a locally hosted, multi-user LLM serving platform on a Jetson Orin Nano. It uses a quantized
Llama model and llama.cpp for inference, a FastAPI gateway for control, and a web chat interface.
The platform evaluates request queuing, continuous batching, configurable parallel slots,
memory-efficient KV caching and quantization, and shows how several clients can share one loaded
model with acceptable latency on constrained hardware.

## Objectives
1. Deploy a quantized LLM locally and run inference without a cloud API.
2. Serve the model through an HTTP endpoint.
3. Build a FastAPI backend with access control, limits and streaming.
4. Build a multi-user web chat frontend with separate sessions.
5. Enable and evaluate concurrent request processing and continuous batching.
6. Optimize memory use (context length, slot count, KV-cache quantization).
7. Implement and test request queuing and overload behaviour.
8. Benchmark time to first token, per-user speed, total throughput and memory.
9. Compare a 3B and an 8B model on the same hardware.
10. Expose the chatbot through a public URL and document the result.
