from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.activities import (
        ask_customer,
        check_isa_allowance,
        check_proof_of_address,
        decide_next_step,
        get_product_details,
        open_account,
        present_options,
        record_consent,
        screen_sanctions,
        search_products,
        verify_identity,
    )
    from app.agent import DISCLAIMER, MAX_TURNS
    from app.models import AgentReply, Customer, KycInput

TASK_QUEUE = "investment-demo"
TIMEOUT = timedelta(seconds=30)

# The only tools the agent may call. Anything else is refused.
TOOLS = {
    "ask_customer": ask_customer,
    "search_products": search_products,
    "get_product_details": get_product_details,
    "check_isa_allowance": check_isa_allowance,
    "present_options": present_options,
}


@workflow.defn
class InvestmentSessionWorkflow:
    """The dynamic part. The agent chooses which tool to use next."""

    def __init__(self) -> None:
        self.history: list[dict] = []
        self.customer_message: str | None = None
        self.agent_replies: list[AgentReply] = []

    @workflow.run
    async def run(self, customer: Customer) -> list[dict]:
        options: list[dict] = []
        await self.wait_for_customer()

        for turn in range(MAX_TURNS):
            final_turn = turn == MAX_TURNS - 1
            decision = await workflow.execute_activity(
                decide_next_step, args=[self.history, final_turn],
                start_to_close_timeout=TIMEOUT,
                summary=f"Turn {turn + 1}: agent decides"
                + (" (must present options)" if final_turn else ""),
            )
            self.history.append({"role": "agent", **decision})
            tool, args = decision["tool"], decision["args"]

            if tool not in TOOLS:
                self.history.append({"role": "tool", "tool": tool, "result": "Unknown tool"})
                continue

            result = await workflow.execute_activity(
                TOOLS[tool], args, start_to_close_timeout=TIMEOUT, summary=describe(tool, args)
            )
            self.history.append({"role": "tool", "tool": tool, "result": result})

            if tool == "ask_customer":
                self.reply(args["question"])
                await self.wait_for_customer()
            elif tool == "present_options":
                options = args["options"]
                self.reply(format_options(args), finished=True)
                break

        await workflow.wait_condition(workflow.all_handlers_finished)
        return options

    @workflow.update
    async def customer_says(self, text: str) -> AgentReply:
        """The customer types a message; returns the agent's next reply."""
        self.customer_message = text
        replies_so_far = len(self.agent_replies)
        await workflow.wait_condition(lambda: len(self.agent_replies) > replies_so_far)
        return self.agent_replies[-1]

    async def wait_for_customer(self) -> None:
        workflow.set_current_details("Waiting for the customer to reply")
        await workflow.wait_condition(lambda: self.customer_message is not None)
        self.history.append({"role": "customer", "text": self.customer_message})
        self.customer_message = None

    def reply(self, text: str, finished: bool = False) -> None:
        self.agent_replies.append(AgentReply(text, finished))


def describe(tool: str, args: dict) -> str:
    """One-line label for the Temporal UI, so the history reads as the agent's path."""
    match tool:
        case "ask_customer":
            return f"Ask customer: {args['question']}"
        case "search_products":
            access = ", easy access" if args["needs_access"] else ""
            return f"Search products: {args['risk_level']} risk, {args['horizon_years']} years{access}"
        case "get_product_details":
            return f"Product details: {args['product_id']}"
        case "check_isa_allowance":
            return "Check remaining ISA allowance"
        case "present_options":
            return "Present options: " + ", ".join(o["name"] for o in args["options"])
    return tool


def format_options(args: dict) -> str:
    lines = [args["explanation"]]
    lines += [f"  {i}. {o['name']}" for i, o in enumerate(args["options"], 1)]
    lines.append(DISCLAIMER)
    return "\n".join(lines)


@workflow.defn
class KycWorkflow:
    """The fixed part. Same checks, same order, every customer."""

    @workflow.run
    async def run(self, kyc: KycInput) -> list[str]:
        return [
            await workflow.execute_activity(verify_identity, kyc, start_to_close_timeout=TIMEOUT),
            await workflow.execute_activity(check_proof_of_address, kyc, start_to_close_timeout=TIMEOUT),
            await workflow.execute_activity(screen_sanctions, kyc, start_to_close_timeout=TIMEOUT),
            await workflow.execute_activity(record_consent, kyc, start_to_close_timeout=TIMEOUT),
            await workflow.execute_activity(open_account, kyc, start_to_close_timeout=TIMEOUT),
        ]
