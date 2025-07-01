
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2, Key } from 'lucide-react';

interface ApiKey {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
}

interface ApiKeysCardProps {
  apiKeys: ApiKey[];
  onGenerateApiKey: () => void;
  onDeleteApiKey: (id: string) => void;
}

export const ApiKeysCard: React.FC<ApiKeysCardProps> = ({
  apiKeys,
  onGenerateApiKey,
  onDeleteApiKey,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>API Keys</CardTitle>
        <CardDescription>
          Generate API keys for your local processor application
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={onGenerateApiKey}>
          <Key className="h-4 w-4 mr-2" />
          Generate New API Key
        </Button>

        {apiKeys.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-medium">Active API Keys</h4>
            {apiKeys.map((key) => (
              <div key={key.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium">{key.name}</p>
                  <p className="text-sm text-gray-600">
                    Created: {new Date(key.created_at).toLocaleDateString()}
                    {key.last_used_at && ` • Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => onDeleteApiKey(key.id)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
