import { useState, type KeyboardEvent } from 'react';
import {
  Code,
  Server,
  Shield,
  Cloud,
  BarChart3,
  Users,
  Check,
  X,
} from 'lucide-react';
import type { UserRole, ExperienceLevel, GuideRequest } from '../types';

interface RoleConfiguratorProps {
  product: 'stripe';
  onGenerate: (request: GuideRequest) => void;
  onBack: () => void;
}

const roles: { role: UserRole; label: string; Icon: typeof Code; description: string }[] = [
  { role: 'frontend_developer', label: 'Frontend Dev', Icon: Code, description: 'Client-side integration with Elements and Checkout' },
  { role: 'backend_developer', label: 'Backend Dev', Icon: Server, description: 'Server-side API integration and payment flows' },
  { role: 'security_engineer', label: 'Security Engineer', Icon: Shield, description: 'API security, PCI compliance, and fraud prevention' },
  { role: 'devops_engineer', label: 'DevOps Engineer', Icon: Cloud, description: 'Infrastructure, monitoring, and deployment' },
  { role: 'product_manager', label: 'Product Manager', Icon: BarChart3, description: 'Capabilities overview and integration planning' },
  { role: 'team_lead', label: 'Team Lead', Icon: Users, description: 'Architecture decisions and team onboarding strategy' },
];

const suggestedFocusAreas: Record<UserRole, string[]> = {
  frontend_developer: ['Stripe Elements', 'Payment forms', 'Client-side validation', 'Checkout UX', 'Mobile payments'],
  backend_developer: ['Payment intents', 'Subscriptions', 'Webhooks', 'Idempotency', 'Error handling'],
  security_engineer: ['API security', 'PCI compliance', 'Audit logging', 'Fraud prevention', 'Encryption'],
  devops_engineer: ['Monitoring', 'CI/CD', 'Key management', 'Load testing', 'Incident response'],
  product_manager: ['Pricing models', 'Payment methods', 'Global expansion', 'Analytics', 'Compliance'],
  team_lead: ['Architecture', 'Team onboarding', 'Best practices', 'Migration strategy', 'Code review'],
};

const suggestedTechStack = ['Python', 'Node.js', 'Go', 'Ruby', 'Java'];

const experienceLevels: { value: ExperienceLevel; label: string }[] = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
];

function TagInput({
  tags,
  onAdd,
  onRemove,
  suggestions,
  placeholder,
}: {
  tags: string[];
  onAdd: (tag: string) => void;
  onRemove: (tag: string) => void;
  suggestions: string[];
  placeholder: string;
}) {
  const [input, setInput] = useState('');

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && input.trim()) {
      e.preventDefault();
      if (!tags.includes(input.trim())) {
        onAdd(input.trim());
      }
      setInput('');
    }
    if (e.key === 'Backspace' && !input && tags.length > 0) {
      onRemove(tags[tags.length - 1]);
    }
  }

  const availableSuggestions = suggestions.filter((s) => !tags.includes(s));

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 p-2 rounded-lg border border-slate-300 bg-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 min-h-[42px]">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-blue-50 text-blue-700 px-2 py-0.5 text-sm"
          >
            {tag}
            <button
              onClick={() => onRemove(tag)}
              className="text-blue-400 hover:text-blue-600 cursor-pointer"
            >
              <X size={12} />
            </button>
          </span>
        ))}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] text-sm outline-none bg-transparent text-slate-900 placeholder:text-slate-400"
        />
      </div>
      {availableSuggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {availableSuggestions.map((s) => (
            <button
              key={s}
              onClick={() => onAdd(s)}
              className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100 hover:border-slate-300 transition-colors cursor-pointer"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function RoleConfigurator({ product, onGenerate, onBack }: RoleConfiguratorProps) {
  const [selectedRole, setSelectedRole] = useState<UserRole | null>(null);
  const [experience, setExperience] = useState<ExperienceLevel>('intermediate');
  const [focusAreas, setFocusAreas] = useState<string[]>([]);
  const [techStack, setTechStack] = useState<string[]>([]);

  function handleGenerate() {
    if (!selectedRole) return;
    onGenerate({
      product,
      role: selectedRole,
      experience_level: experience,
      focus_areas: focusAreas,
      tech_stack: techStack,
    });
  }

  return (
    <div className="max-w-5xl mx-auto">
      <button
        onClick={onBack}
        className="text-sm text-slate-500 hover:text-slate-700 mb-6 cursor-pointer"
      >
        ← Back to products
      </button>

      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-slate-900 mb-2">Configure Your Guide</h2>
        <p className="text-slate-500">Select your role and customize the guide to your needs</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left column — Role selection */}
        <div>
          <h3 className="text-sm font-medium text-slate-700 mb-3">Select Role</h3>
          <div className="grid grid-cols-2 gap-3">
            {roles.map(({ role, label, Icon, description }) => {
              const isSelected = selectedRole === role;
              return (
                <button
                  key={role}
                  onClick={() => {
                    setSelectedRole(role);
                    setFocusAreas([]);
                  }}
                  className={`relative rounded-xl border p-4 text-left transition-all cursor-pointer ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50 shadow-sm'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center">
                      <Check size={12} className="text-white" />
                    </div>
                  )}
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${
                    isSelected ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-500'
                  }`}>
                    <Icon size={16} />
                  </div>
                  <p className={`text-sm font-medium ${isSelected ? 'text-blue-900' : 'text-slate-900'}`}>
                    {label}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right column — Configuration */}
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-3">Experience Level</h3>
            <div className="flex rounded-lg border border-slate-200 overflow-hidden">
              {experienceLevels.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => setExperience(value)}
                  className={`flex-1 py-2 text-sm font-medium transition-colors cursor-pointer ${
                    experience === value
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-2">Focus Areas</h3>
            <TagInput
              tags={focusAreas}
              onAdd={(tag) => setFocusAreas((prev) => [...prev, tag])}
              onRemove={(tag) => setFocusAreas((prev) => prev.filter((t) => t !== tag))}
              suggestions={selectedRole ? suggestedFocusAreas[selectedRole] : []}
              placeholder="Type and press Enter to add..."
            />
          </div>

          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-2">Tech Stack</h3>
            <TagInput
              tags={techStack}
              onAdd={(tag) => setTechStack((prev) => [...prev, tag])}
              onRemove={(tag) => setTechStack((prev) => prev.filter((t) => t !== tag))}
              suggestions={suggestedTechStack}
              placeholder="Type and press Enter to add..."
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={!selectedRole}
            className={`w-full py-3 rounded-lg font-medium transition-colors text-sm ${
              selectedRole
                ? 'bg-blue-600 text-white hover:bg-blue-700 cursor-pointer'
                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
            }`}
          >
            Generate Guide
          </button>
        </div>
      </div>
    </div>
  );
}
