def load_model(args, name=None):
    from .llms import API_LLM
    return API_LLM(name or args.llm, args.temperature, args.max_tokens, args.top_p)
