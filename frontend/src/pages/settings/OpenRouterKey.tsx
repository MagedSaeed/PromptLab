import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Key, Eye, EyeOff, Trash2, Save } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import PageLayout from '@/components/layout/PageLayout';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function OpenRouterKey() {
  const { user, checkAuth } = useAuth();
  const [newKey, setNewKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const saveMutation = useMutation({
    mutationFn: async (key: string) => {
      const res = await api.put('/openrouter/api-key/', { openrouter_api_key: key });
      return res.data;
    },
    onSuccess: async () => {
      setMessage({ type: 'success', text: 'API key saved successfully.' });
      setNewKey('');
      await checkAuth();
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: Record<string, unknown> }; message?: string };
      const detail =
        axiosErr.response?.data
          ? Object.values(axiosErr.response.data).flat().join(' ')
          : axiosErr.message || 'Failed to save API key.';
      setMessage({ type: 'error', text: detail });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const res = await api.delete('/openrouter/api-key/delete/');
      return res.data;
    },
    onSuccess: async () => {
      setMessage({ type: 'success', text: 'API key deleted successfully.' });
      setNewKey('');
      await checkAuth();
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: Record<string, unknown> }; message?: string };
      const detail =
        axiosErr.response?.data
          ? Object.values(axiosErr.response.data).flat().join(' ')
          : axiosErr.message || 'Failed to delete API key.';
      setMessage({ type: 'error', text: detail });
    },
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim()) return;
    setMessage(null);
    saveMutation.mutate(newKey.trim());
  };

  const handleDelete = () => {
    setMessage(null);
    deleteMutation.mutate();
  };

  const maskedKey = user?.masked_openrouter_api_key;
  const isPending = saveMutation.isPending || deleteMutation.isPending;

  return (
    <PageLayout
      title="Settings"
      breadcrumbs={[{ label: 'Settings' }]}
    >
      <div className="max-w-xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              OpenRouter API Key
            </CardTitle>
            <CardDescription>
              Configure your OpenRouter API key for LLM testing. The key is stored securely and
              never displayed in full after saving.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Current Key Status */}
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Current Key</Label>
              {maskedKey ? (
                <div className="flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-2">
                  <code className="flex-1 text-sm font-mono">
                    {showKey ? maskedKey : maskedKey}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowKey(!showKey)}
                    className="h-7 w-7 p-0"
                  >
                    {showKey ? (
                      <EyeOff className="h-3.5 w-3.5" />
                    ) : (
                      <Eye className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground italic">No API key configured.</p>
              )}
            </div>

            {/* Save New Key */}
            <form onSubmit={handleSave} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="new_key">
                  {maskedKey ? 'Replace API Key' : 'Add API Key'}
                </Label>
                <Input
                  id="new_key"
                  type="password"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="sk-or-v1-..."
                  autoComplete="off"
                />
              </div>
              <Button type="submit" disabled={isPending || !newKey.trim()}>
                {saveMutation.isPending ? (
                  'Saving...'
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Save Key
                  </>
                )}
              </Button>
            </form>

            {/* Delete Key */}
            {maskedKey && (
              <div className="border-t pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Remove API Key</p>
                    <p className="text-xs text-muted-foreground">
                      This will remove your stored API key. LLM testing will be disabled.
                    </p>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleDelete}
                    disabled={isPending}
                  >
                    {deleteMutation.isPending ? (
                      'Deleting...'
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Messages */}
            {message && (
              <div
                className={`rounded-lg p-3 text-sm ${
                  message.type === 'success'
                    ? 'bg-green-50 text-green-800 border border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800'
                    : 'bg-destructive/10 text-destructive border border-destructive/30'
                }`}
              >
                {message.text}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
