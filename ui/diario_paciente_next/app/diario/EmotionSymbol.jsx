import {
  Activity,
  Ban,
  CircleDot,
  CloudDrizzle,
  CloudFog,
  CloudRain,
  Citrus,
  Droplet,
  Flame,
  FlameKindling,
  Frown,
  HeartHandshake,
  Leaf,
  Lightbulb,
  PartyPopper,
  Search,
  Scale,
  Shield,
  ShieldAlert,
  ShieldQuestion,
  Sparkles,
  Sunrise,
  Swords,
  Waves,
  Zap,
} from "lucide-react";
import { getEmotionProfile, getSubEmotionProfile } from "../lib/emotionTaxonomy";

const emotionIcons = {
  alegria: Sunrise,
  tristeza: CloudRain,
  medo: ShieldAlert,
  raiva: Flame,
  nojinho: Citrus,
  neutro: CircleDot,
  surpresa: PartyPopper,
};

const subEmotionIcons = {
  gratidao: HeartHandshake,
  otimismo: Sunrise,
  entusiasmo: Sparkles,
  desanimo: CloudDrizzle,
  luto: Droplet,
  decepcao: CloudFog,
  ansiedade: Activity,
  panico: Zap,
  inseguranca: ShieldQuestion,
  irritacao: Flame,
  indignacao: Swords,
  furia: FlameKindling,
  aversao: Shield,
  desconforto: Frown,
  desprezo: Ban,
  equilibrio: Scale,
  serenidade: Waves,
  sobriedade: Leaf,
  espanto: PartyPopper,
  curiosidade: Search,
  descoberta: Lightbulb,
};

export default function EmotionSymbol({ emotion, subEmotion, size = 22, className }) {
  const profile = getEmotionProfile(emotion);
  const sub = getSubEmotionProfile(profile.id, subEmotion);
  const Icon = (sub && subEmotionIcons[sub.id]) || emotionIcons[profile.id] || CircleDot;

  return (
    <Icon
      aria-hidden="true"
      className={className}
      size={size}
      strokeWidth={1.8}
      focusable="false"
    />
  );
}
