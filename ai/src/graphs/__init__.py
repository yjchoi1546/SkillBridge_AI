"""LangGraph 워크플로. LangGraph 의존은 각 그래프의 graph.py 에만 둔다.

노드는 `async def node(state) -> dict` 순수 함수로 작성한다 — 오케스트레이터를 바꿔도 노드는 그대로 쓴다.
"""
