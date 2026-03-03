import { CreditCard, Phone, Mail } from 'lucide-react';
import type { SupportedProduct } from '../types';

interface ProductSelectorProps {
  onSelect: (product: SupportedProduct) => void;
}

const products = [
  {
    id: 'stripe' as SupportedProduct,
    name: 'Stripe',
    description: 'Payment processing, subscriptions, and financial infrastructure',
    Icon: CreditCard,
    available: true,
    docCount: 2847,
    chunkCount: 12430,
  },
  {
    id: 'twilio' as SupportedProduct,
    name: 'Twilio',
    description: 'Communication APIs for SMS, voice, and video',
    Icon: Phone,
    available: false,
    docCount: 0,
    chunkCount: 0,
  },
  {
    id: 'sendgrid' as SupportedProduct,
    name: 'SendGrid',
    description: 'Email delivery and marketing campaign management',
    Icon: Mail,
    available: false,
    docCount: 0,
    chunkCount: 0,
  },
];

export function ProductSelector({ onSelect }: ProductSelectorProps) {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-10">
        <h2 className="text-2xl font-semibold text-slate-900 mb-2">
          Choose a Product
        </h2>
        <p className="text-slate-500">
          Select the product you want to generate an onboarding guide for
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {products.map(({ id, name, description, Icon, available, docCount, chunkCount }) => (
          <button
            key={id}
            onClick={() => available && onSelect(id)}
            disabled={!available}
            className={`relative rounded-xl border bg-white p-6 text-left transition-all ${
              available
                ? 'border-slate-200 shadow-sm hover:shadow-md hover:border-blue-300 cursor-pointer'
                : 'border-slate-100 opacity-50 cursor-not-allowed'
            }`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50 text-blue-600">
                <Icon size={20} />
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  available
                    ? 'bg-green-100 text-green-700'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {available ? 'Available' : 'Coming Soon'}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 mb-1">{name}</h3>
            <p className="text-sm text-slate-500 mb-4">{description}</p>
            {available && (
              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span>{docCount.toLocaleString()} docs</span>
                <span className="w-1 h-1 rounded-full bg-slate-300" />
                <span>{chunkCount.toLocaleString()} chunks</span>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
