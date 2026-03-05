from agents import HonestAgent, SybilAttacker

def run_simulation(steps=1000, probation_period=180, bond_amount=500, reward_percentage=0.15, burn_ratio=0.25):
    # Constants
    integrity_reward = bond_amount * reward_percentage
    total_slash_amount = bond_amount * 2
    burn_amount = total_slash_amount * burn_ratio
    compensation_amount = total_slash_amount * (1 - burn_ratio)

    # Initialization
    honest_agents = [HonestAgent(f"Honest_{i}") for i in range(50)]
    sybil_attackers = [SybilAttacker(f"Sybil_{i}") for i in range(3)]

    # Metrics
    total_cre_burned = 0
    total_cre_compensated = 0
    successful_graduations = 0
    total_defaults = 0

    candidate_id_counter = 0

    for step in range(1, steps + 1):
        # 1. Process Graduations
        for agent in honest_agents:
            # Note: We iterate over a copy to safely remove items from active_bonds
            for candidate in list(agent.active_bonds):
                if step - candidate.start_step >= probation_period:
                    agent.process_graduation(candidate, integrity_reward)
                    successful_graduations += 1

        for attacker in sybil_attackers:
            # We assume attackers default immediately and don't graduate,
            # but in case we want them to optionally graduate later we leave this here.
            for fake in list(attacker.active_fakes):
                if step - fake.start_step >= probation_period:
                    attacker.graduate_fake(fake, integrity_reward)
                    successful_graduations += 1

        # 2. Process Sybil Actions
        for attacker in sybil_attackers:
            new_fake = attacker.spawn_and_sponsor_fake(step, f"Fake_{candidate_id_counter}", bond_amount)
            if new_fake:
                candidate_id_counter += 1

                # Attacker defaults immediately to steal principal
                # In this specific scenario, they default right after spawning to lock in stolen principal
                # and trigger the slash.
                attacker.execute_default(new_fake, stolen_principal=500)

                # Slashing occurs
                total_cre_burned += burn_amount
                total_cre_compensated += compensation_amount
                total_defaults += 1

        # 3. Process Honest Actions
        for agent in honest_agents:
            new_candidate = agent.try_sponsor(step, f"Cand_{candidate_id_counter}", bond_amount)
            if new_candidate:
                candidate_id_counter += 1
                # Honest agents don't default, they just wait for graduation.

    # End of Simulation - Telemetry
    print("--- Simulation Complete ---")
    print(f"Total $CRE Burned: {total_cre_burned:.2f}")
    print(f"Total $CRE Compensated to Victims: {total_cre_compensated:.2f}")
    print(f"Total Successful Graduations: {successful_graduations}")
    print(f"Total Defaults: {total_defaults}")

    print("\n--- Attacker ROI ---")
    for attacker in sybil_attackers:
        roi = attacker.balance - attacker.initial_balance
        print(f"{attacker.id}: Final Balance = {attacker.balance:.2f}, ROI = {roi:.2f}")

if __name__ == "__main__":
    run_simulation()
