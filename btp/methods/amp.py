from btp.methods.base import BaseStrategy
from src.language import load_model
from btp.methods.utils import parse_json_output, markdown_to_rows
from btp.prompts.amp_prompts import get_analysis_prompt, get_constraint_prompt, get_generation_prompt, get_validation_prompt

class AMP_Strategy(BaseStrategy):
    """
    Adaptive Multi-Stage Prompting (AMP) Strategy.
    Implements 4 stages: Analysis, Constraint Discovery, Generation, Self-Validation.
    """
    def __init__(self, data, args):
        super().__init__(data, args)
        self.model = getattr(args, 'pipeline', None)
        if self.model is None:
            self.model = load_model(args, name=args.llm).get_pipeline()
        # Parse ablation mode from args or env (default to full AMP-4)
        self.mode = getattr(args, 'amp_mode', 'AMP-4') 

    def generate_examples(self, best_rows, rest_rows):
        # x-features only: used for generation output schema
        x_features_desc = []
        for c in self.data.cols.x:
            if hasattr(c, 'lo'): # NUM
                x_features_desc.append(f"- {c.txt} (Feature): {c.lo} to {c.hi}")
            else: # SYM
                vals = list(c.has.keys()) if c.has else []
                if len(vals) < 10:
                    x_features_desc.append(f"- {c.txt} (Feature): Categorical {vals}")
                else:
                    x_features_desc.append(f"- {c.txt} (Feature): Categorical (many values)")
        
        # Full description including objectives: used for analysis/reasoning
        objectives_desc = []
        for c in self.data.cols.y:
            direction = "Maximize" if (hasattr(c, 'w') and c.w > 0) else "Minimize"
            if hasattr(c, 'lo'): # NUM
                objectives_desc.append(f"- {c.txt} (Objective - {direction}): {c.lo} to {c.hi}")
            else: # SYM
                objectives_desc.append(f"- {c.txt} (Objective - {direction}): Categorical")
        
        x_features_str = "\n".join(x_features_desc)
        full_desc = x_features_str + "\n\nObjectives (for context, do NOT generate values for these):\n" + "\n".join(objectives_desc)
        
        res_best, res_rest = [], []
        
        # Stage 1: Analysis — give full context (features + objectives)
        analysis_prompt = get_analysis_prompt(full_desc, best_rows, rest_rows)
        analysis = self.model.invoke(analysis_prompt).content
        
        if self.mode == 'AMP-2':
            # Skip C & V
            constraints = "No explicit constraints."
            gen_prompt = get_generation_prompt(analysis, constraints, best_rows, x_features_str)
            gen_response = self.model.invoke(gen_prompt).content
            draft_best, draft_rest = self._parse_response(gen_response)
            return draft_best + draft_rest

        # Stage 2: Constraint Discovery — uses analysis (which already has objective context)
        constraint_prompt = get_constraint_prompt(analysis)
        constraints = self.model.invoke(constraint_prompt).content
        
        if self.mode == 'AMP-3':
            # Skip V
            gen_prompt = get_generation_prompt(analysis, constraints, best_rows, x_features_str)
            gen_response = self.model.invoke(gen_prompt).content
            print(f"\n[DEBUG R1] AMP-3 Raw Gen Response:\n{gen_response}\n[DEBUG END]")
            draft_best, draft_rest = self._parse_response(gen_response)
            return draft_best + draft_rest

        # Stage 3: Generation — only x-features in the output schema
        gen_prompt = get_generation_prompt(analysis, constraints, best_rows, x_features_str)
        gen_response = self.model.invoke(gen_prompt).content
        print(f"\n[DEBUG R1] AMP-4 Raw Gen Response:\n{gen_response}\n[DEBUG END]")
        
        draft_best, draft_rest = self._parse_response(gen_response)
        if not draft_best: return [], []
        
        # Stage 4: Self-Validation (Iterative Refinement)
        final_best = []
        for ex in draft_best:
            val_prompt = get_validation_prompt(constraints, ex)
            val_res = self.model.invoke(val_prompt).content
            parsed_val = parse_json_output(val_res)
            
            if parsed_val.get("status") == "INVALID" and "revised_features" in parsed_val:
                final_best.append(parsed_val["revised_features"])
            else:
                final_best.append(ex)

        final_rest = [] # Similarly validate rest? Usually we focus on 'best' for constraints but paper says "Verification... Each generated example".
        pass 
        # For brevity/cost, let's assume we validate 'rest' too or just pass them.
        # Paper says "refinement... if a config violates a hard constraint".
        # Let's validate rest too.
        for ex in draft_rest:
             val_prompt = get_validation_prompt(constraints, ex)
             val_res = self.model.invoke(val_prompt).content
             parsed_val = parse_json_output(val_res)
             if parsed_val.get("status") == "INVALID" and "revised_features" in parsed_val:
                final_rest.append(parsed_val["revised_features"])
             else:
                final_rest.append(ex)

        return final_best + final_rest # Return combined logic as before

    def _parse_response(self, response):
        if not isinstance(response, str) or not response.strip():
            return [], []
        if "better_examples" in response:
            data = parse_json_output(response)
            best_new = [x['features'] for x in data.get('better_examples', [])]
            rest_new = [x['features'] for x in data.get('poorer_examples', [])]
            return best_new, rest_new
        else:
            return markdown_to_rows(response)
