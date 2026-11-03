import { FeatureSection } from "@/components/landing/FeatureSection";
import { FinalCta } from "@/components/landing/FinalCta";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorks } from "@/components/landing/HowItWorks";

export default function HomePage() {
  return (
    <main>
      <HeroSection />
      <FeatureSection />
      <HowItWorks />
      <FinalCta />
    </main>
  );
}
