#!/usr/bin/env python3
"""Quick verification script for Phase 2 structure.

Tests imports and basic structure without making actual API calls.
"""

def test_imports():
    """Test that all Phase 2 modules can be imported."""
    print("Testing imports...")

    try:
        # Test arbitrage module imports
        from openbet.arbitrage import (
            Constraint,
            ConsensusResult,
            DependencyAnalysisResponse,
            DependencyContext,
            DependencyDetector,
        )
        print("✓ Arbitrage module imports successful")

        # Test LLM providers have new method
        from openbet.llm.base import BaseLLMProvider
        from openbet.llm.claude import ClaudeProvider
        from openbet.llm.openai import OpenAIProvider
        from openbet.llm.grok import GrokProvider
        from openbet.llm.gemini import GeminiProvider

        # Check that analyze_custom_prompt exists
        assert hasattr(BaseLLMProvider, 'analyze_custom_prompt')
        print("✓ BaseLLMProvider has analyze_custom_prompt")

        # Test repositories
        from openbet.database.repositories import (
            EventRepository,
            EventDependencyRepository,
            ArbitrageOpportunityRepository,
        )
        print("✓ Repository imports successful")

        # Test Kalshi client has Events API
        from openbet.kalshi.client import KalshiClient
        from openbet.kalshi.models import Event

        assert hasattr(KalshiClient, 'get_events')
        assert hasattr(KalshiClient, 'get_event')
        print("✓ KalshiClient has Events API methods")

        print("\n✅ All imports successful!")
        return True

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test that Pydantic models can be instantiated."""
    print("\nTesting models...")

    try:
        from openbet.arbitrage.models import (
            Constraint,
            DependencyContext,
            DependencyAnalysisResponse,
        )

        # Test Constraint
        constraint = Constraint(
            constraint_type="implication",
            description="Event A implies Event B",
            formal_expression="A => B",
            confidence=0.8
        )
        assert constraint.confidence == 0.8
        print("✓ Constraint model works")

        # Test DependencyContext
        context = DependencyContext(
            event_a_ticker="TEST-A",
            event_a_title="Test Event A",
            event_b_ticker="TEST-B",
            event_b_title="Test Event B",
            same_series=False
        )
        prompt_text = context.to_prompt_text()
        assert "TEST-A" in prompt_text
        print("✓ DependencyContext model works")

        # Test DependencyAnalysisResponse
        response = DependencyAnalysisResponse(
            dependency_score=0.7,
            is_dependent=True,
            dependency_type="causal",
            constraints=[constraint],
            reasoning="Test reasoning",
            provider="test"
        )
        assert response.is_dependent
        print("✓ DependencyAnalysisResponse model works")

        print("\n✅ All models work correctly!")
        return True

    except Exception as e:
        print(f"\n❌ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_schema():
    """Test that database tables exist."""
    print("\nTesting database schema...")

    try:
        from openbet.database.models import ALL_TABLES

        # Check that new tables are included
        table_sql = "\n".join(ALL_TABLES)

        assert "CREATE TABLE IF NOT EXISTS events" in table_sql
        print("✓ events table defined")

        assert "CREATE TABLE IF NOT EXISTS event_dependencies" in table_sql
        print("✓ event_dependencies table defined")

        assert "CREATE TABLE IF NOT EXISTS arbitrage_opportunities" in table_sql
        print("✓ arbitrage_opportunities table defined")

        # Check for indexes
        assert "idx_events_category" in table_sql
        assert "idx_event_deps_a" in table_sql
        assert "idx_arbitrage_status" in table_sql
        print("✓ All indexes defined")

        print("\n✅ Database schema complete!")
        return True

    except Exception as e:
        print(f"\n❌ Database schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_commands():
    """Test that CLI commands are registered."""
    print("\nTesting CLI commands...")

    try:
        from openbet.cli import cli

        # Get list of registered commands
        command_names = list(cli.commands.keys())

        # Check for new Phase 2 commands
        required_commands = [
            'get-events',
            'detect-dependencies',
            'list-dependencies',
            'verify-dependency',
        ]

        for cmd in required_commands:
            assert cmd in command_names, f"Command {cmd} not found"
            print(f"✓ {cmd} command registered")

        print("\n✅ All CLI commands registered!")
        return True

    except Exception as e:
        print(f"\n❌ CLI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Phase 2 Structure Verification")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Models", test_models()))
    results.append(("Database Schema", test_database_schema()))
    results.append(("CLI Commands", test_cli_commands()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 Phase 2 structure verification complete!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set environment variables for API keys")
        print("3. Test with: openbet get-events --status=open")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
