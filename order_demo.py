"""Interactive Chinese reservation demo. SQLite inventory exists only for this session."""
import argparse
from contextlib import closing
import json

from order_eval import connect, decode_batch, message
from order_session import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",action="store_true",help="use existing ChatGPT login for extraction")
    args = parser.parse_args()
    client = None
    if args.model:
        client,version = connect()
        print("本次提取程序",version)
    print("合成库存演示。示例：请预留茶，有效期不早于2026-12-01，优先早到期。")
    print("可以回答单个待确认字段，或用“重下：”提交完整修订。输入“退出”结束。")
    session = Session()
    dialogue = []
    with closing(session.db):
        for _ in range(12):
            try:
                text = input("> ").strip()
            except EOFError:
                break
            if text=="退出":
                break
            if text.startswith("确认 "):
                view = session.confirm(text)
            else:
                session.pending = None
                if len(text)>600:
                    print("输入过长，本次会话已结束。")
                    break
                dialogue.append(text)
                if client:
                    try:
                        client.request(message([dialogue]),1600)
                    except (OSError,RuntimeError,TimeoutError) as exc:
                        print("模型调用中止",type(exc).__name__)
                        break
                    reply = client.calls[-1]["reply"]
                    proposal = decode_batch(reply,1)[0] if len(reply)<=1600 else None
                else:
                    proposal = session.proof_for(text)
                view = session.interpret(text,proposal)
            if view["state"]=="ask":
                dialogue.append(view["question"])
                print(view["question"])
            elif view["state"]=="preview":
                print("请核对商品、数量、最低有效日期、到期优先级：",json.dumps(view["slots"],ensure_ascii=False))
                print("仅在同意上述订单时输入：确认",view["nonce"])
            else:
                print(json.dumps(view,ensure_ascii=False))
            if session.closed:
                break


if __name__=="__main__":
    main()
