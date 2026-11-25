import unittest
from unittest.mock import patch

from order_language import evidence, schema
from order_session import Session
from order_eval import ROOT, decode_batch, matches_authorized_fill, metrics, paired, read, proposals

ORDER = "请预留茶，要3件，有效期不早于2026-12-02，优先早到期。"


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.session=Session()
        self.addCleanup(self.session.db.close)
        self.before=self.session.rows()

    def submit(self,text,p=None):
        return self.session.interpret(text,evidence(text) if p is None else p)

    def test_invalid_model_reply(self):
        for raw in ('[{"qty":1,"qty":2}]', 'not json', '[', '[1,2]'):
            self.assertEqual(decode_batch(raw,1),[None])
        for value in [None,"not JSON",[],{"done":True},True,{"state":"filled"}]:
            self.assertEqual(self.session.interpret("重下："+ORDER,value)["state"],"blocked")
        self.assertEqual(proposals({},2),[None,None])
        self.assertEqual(self.session.rows(),self.before)

    def test_evaluator_detects_wrong_committed_lot(self):
        view=self.submit(ORDER)
        self.session.confirm("确认 "+view["nonce"])
        actual=self.session.rows()
        self.assertTrue(matches_authorized_fill(self.before,actual,view["slots"]))
        bad=list(actual)
        bad[0]=self.before[0]
        self.assertFalse(matches_authorized_fill(self.before,bad,view["slots"]))

    def test_schema_domain_and_types(self):
        for key,bad in [("qty",-2),("qty",0),("qty",21),("qty",True),("qty","3"),("sku","咖啡"),
                        ("date","2026-02-30"),("priority","any")]:
            p=evidence(ORDER)
            p["slots"][key]=bad
            self.assertFalse(schema(p))
            self.assertEqual(self.submit("重下："+ORDER,p)["state"],"blocked")
        self.assertEqual(self.session.rows(),self.before)

    def test_missing_and_conflicting_slots(self):
        for text,key in [(ORDER.replace("要3件，",""),"qty"),(ORDER.replace("有效期不早于2026-12-02，",""),"date"),
                         (ORDER+"同时优先晚到期","priority"),(ORDER.replace("要3件","3件或5件"),"qty")]:
            view=self.submit("重下："+text)
            self.assertEqual((view["state"],view["target"]),("ask",key))
        self.assertEqual(self.session.rows(),self.before)

    def test_unsupported_extra_request_and_unknown_product(self):
        for text in (ORDER+"送到我家",ORDER.replace("茶","梨"),ORDER.replace("3件","-3件"),"不要"+ORDER):
            self.assertEqual(self.submit("重下："+text,evidence(ORDER))["state"],"refused")
        self.assertEqual(self.session.rows(),self.before)

    def test_unresolved_then_short_answer(self):
        text=ORDER.replace("要3件","3件或5件")
        self.submit(text)
        self.assertEqual(self.submit("都可以",evidence(ORDER))["state"],"blocked")
        self.assertEqual(self.session.confirm("确认")["state"],"blocked")
        self.submit("重下："+text)
        view=self.submit("要3件",evidence(ORDER))
        self.assertEqual(view["state"],"preview")
        self.assertEqual(self.session.rows(),self.before)

    def test_revision_and_external_confirmation(self):
        old=self.submit(ORDER)
        new=self.submit("重下："+ORDER.replace("3件","2件"))
        self.assertNotEqual(old["nonce"],new["nonce"])
        self.assertEqual(self.session.confirm("确认 "+old["nonce"])["state"],"blocked")
        self.assertEqual(self.session.rows(),self.before)
        new=self.submit("重下："+ORDER.replace("3件","2件"))
        cmd="确认 "+new["nonce"]
        self.assertEqual(self.session.confirm(cmd)["state"],"filled")
        after=self.session.rows()
        self.assertEqual(sum(row[-1] for row in after),2)
        self.assertEqual(self.session.confirm(cmd)["state"],"blocked")
        self.assertEqual(self.session.rows(),after)

    def test_fault_rolls_back_sqlite(self):
        view=self.submit(ORDER)
        with patch("order_session.grade",return_value=False), self.assertRaises(RuntimeError):
            self.session.confirm("确认 "+view["nonce"])
        self.assertEqual(self.session.rows(),self.before)

    def test_hallucination_never_authorizes_write(self):
        missing=ORDER.replace("要3件，","")
        self.assertEqual(self.submit(missing,evidence(ORDER))["state"],"blocked")
        self.assertEqual(self.session.confirm("确认 yes")["state"],"blocked")
        self.assertEqual(self.session.rows(),self.before)

    def test_clear_paraphrase_outside_grammar_is_refused(self):
        # Post-hoc scope probe. A semantically correct extraction is still insufficient.
        text="茶要三件，至少能放到2026年12月2日，先挑快到期的。"
        self.assertEqual(self.submit(text,evidence(ORDER))["state"],"refused")
        self.assertEqual(self.session.rows(),self.before)

    def test_independent_labels_and_completeness(self):
        cases=read(ROOT/"orders.jsonl")
        self.assertEqual(len({c["text"] for c in cases}),100)
        self.assertEqual(len({c["id"] for c in cases}),100)
        for split in ("dev","holdout"):
            for kind in ("clear","missing","ambiguous","conflict","unsupported"):
                self.assertEqual(sum((c["split"],c["kind"])==(split,kind) for c in cases),10)
        # Hand-labeled intent must actually be fulfilled by the reference executor.
        for c in cases:
            first={"slots":c["initial"],"kind":c["kind"],"target":c["target"]}
            follow={"slots":c["authorized"],"kind":"clear","target":None}
            row=paired(c,"C",first,follow)
            self.assertFalse(row["unsafe"],c["id"])
            self.assertEqual(row["filled"],c["kind"]!="unsupported",c["id"])

    def test_question_credit_and_invalid_classifier(self):
        clear, missing=read(ROOT/"orders.jsonl")[:2]
        invalid=paired(clear,"B",None)
        self.assertEqual(metrics([invalid],{clear["id"]:clear})["conflict_correct"],0)
        unanswered=dict(missing,answer=None)
        row=paired(unanswered,"C",evidence(missing["text"]))
        self.assertTrue(row["targeted"])
        self.assertFalse(row["write"])
