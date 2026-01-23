from flask import Flask, jsonify, request
from uuid import uuid4
from langgraph.types import Command
from human_in_loop import agent


app = Flask(__name__)

TASK_HISTORY = set()

@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    task_description = data.get("task_description")

    if not task_description:
        return jsonify({"error": "Task description is required"}), 400

    task_id = str(uuid4())
    TASK_HISTORY.add(task_id)
    config = {"configurable": {"thread_id": task_id}}

    stream = agent.stream({"task_description": task_description}, config=config, stream_mode=["updates"]) 

    for mode, chunk in stream:
        print(f"mode", mode)
        print(f"chunk", chunk)
        if mode == "updates" and "__interrupt__" in chunk:
            raw_interrupt = chunk["__interrupt__"]
            if isinstance(raw_interrupt, tuple):
                interrupt_data = raw_interrupt[0]
            
            if "instructions" in interrupt_data.value:
                return jsonify({
                    "task_id": task_id,
                    "status": "Pending User Selection",
                    "question": interrupt_data.value["question"],
                    "answers": [
                        {
                            "option": i + 1,
                            "text": ans
                        }
                        for i, ans in enumerate(interrupt_data.value["answer"])
                    ],
                    "instructions": interrupt_data.value["instructions"],
                })
            
            if "options" in interrupt_data.value:
                return jsonify({
                "task_id": task_id,
                "status": "Pending User Evaluation",
                "question": interrupt_data.value["question"],
                "answer": interrupt_data.value["answer"],
                "options": ["approve", "refine"],
            })
        
    final_state = agent.get_state(config)
    return jsonify({
        "task_id": task_id,
        "status": "Completed",
        "score": final_state.values.get("score"),
        "number of options" : final_state.values.get("number_of_options"),
        "final_answer": final_state.values["answer"],
        })

               
@app.route('/tasks/<task_id>/decision', methods=['POST'])
def submit_decision(task_id):
    data = request.get_json()
    config = {"configurable": {"thread_id": task_id}}

    # ---------- SELECTION ----------
    if "selected_answer" in data:
        stream = agent.stream(
            Command(resume={"selected_answer": data["selected_answer"]}),
            config=config,
            stream_mode=["updates"]
        )

    # ---------- APPROVAL ----------
    elif data.get("decision") in ["approve", "refine"]:
        stream = agent.stream(
            Command(resume={"decision": data["decision"]}),
            config=config,
            stream_mode=["updates"]
        )

    else:
        return jsonify({
            "error": "Must provide either 'selected_answer' or 'decision'"
        }), 400

    for mode, chunk in stream:
        if mode == "updates" and "__interrupt__" in chunk:
            raw_interrupt = chunk["__interrupt__"]
            if isinstance(raw_interrupt, tuple):
                interrupt_data = raw_interrupt[0]
            
            if "instructions" in interrupt_data.value:
                return jsonify({
                    "task_id": task_id,
                    "status": "Pending User Selection",
                    "question": interrupt_data.value["question"],
                    "answers": interrupt_data.value["answer"],
                    "instructions": interrupt_data.value["instructions"],
                })
            
            if "options" in interrupt_data.value:
                return jsonify({
                "task_id": task_id,
                "status": "Pending User Evaluation",
                "question": interrupt_data.value["question"],
                "answer": interrupt_data.value["answer"],
                "options": ["approve", "refine"],
            })
        
    final_state = agent.get_state(config)
    return jsonify({
        "task_id": task_id,
        "status": "Completed",
        "score": final_state.values.get("score"),
        "number of options" : final_state.values.get("number_of_options"),
        "final_answer": final_state.values["final_answer"],
    })

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    config = {"configurable": {"thread_id": task_id}}
    state = agent.get_state(config)

    if not state:
        return jsonify({"error": "Task not found"}), 404

    status = "Completed"
    response = {
        "task_id": task_id,
        "status": status,
        "number_of_options": state.values.get("number_of_options"),
    }

    if state.interrupts:
        interrupt = state.interrupts[-1]  # latest interrupt
        payload = interrupt.value

        answers = payload.get("answer")
        if isinstance(answers, list) and len(answers) > 1:
            response.update({
                "status": "Pending Human Selection",
                "question": payload.get("question"),
                "instructions": payload.get("instructions"),
                "answers": [
                    {
                        "option": i + 1,
                        "answer": ans
                    }
                    for i, ans in enumerate(answers)
                ]
            })
            return jsonify(response)

        response.update({
            "status": "Pending Human Approval",
            "question": payload.get("question"),
            "answer": answers,
            "options": ["approve", "refine"]
        })
        return jsonify(response)

    response.update({
        "final_answer": state.values.get("answer"),
        "score": state.values.get("score"),
        "state": state.values
    })
    return jsonify(response)


all_tasks  = []
@app.route('/', methods=['GET'])
def get_history():

    if TASK_HISTORY is None or len(TASK_HISTORY) == 0:
        return jsonify({
            "total_tasks": 0,
            "tasks": [],
        })

    for task_id in TASK_HISTORY:

        print (len(TASK_HISTORY))

        config = {"configurable": {"thread_id": task_id}}
        try:
            history = agent.get_state_history(config)
        except Exception:
            return jsonify({"error": f"Could not retrieve history for task {task_id}"}), 500

        steps = []
        for i, state_snapshot in enumerate(history):
            
            step = {
                "step": i + 1,
                "node": state_snapshot.metadata.get("node_name", "unknown"),
            }

            if state_snapshot.values:
                step["state"] = state_snapshot.values

            if state_snapshot.interrupts:
                step["interrupts"] = state_snapshot.interrupts[0].value
                step["status"] = "Pending Human Approval"
            else:
                step["status"] = "Completed"

            steps.append(step)

        all_tasks.append({
            "task_id": task_id,
            "history": steps,
        })

    return jsonify({
        "total_tasks": len(all_tasks),
        "tasks": all_tasks,    
    }
)

if __name__ == '__main__':
    app.run(debug=True, port=5001)